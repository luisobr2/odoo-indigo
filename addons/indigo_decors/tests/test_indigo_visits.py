# -*- coding: utf-8 -*-
"""Visitas: que ordenes piden que alguien conduzca hasta casa del cliente.

Lo que se prueba no es que un campo calculado calcule, sino la decision que
el campo toma por el planificador, y sobre todo la que casi se toma mal:

Al analizar esto se conto "41 ordenes esperan medicion" metiendo en el saco
las etapas ANTERIORES a medir — 30 de ellas en 'design_pending', que esperan
que el cliente confirme un diseno, no que nadie coja el coche. La cola real
eran 2. Si esa cuenta se hubiera quedado en el codigo, la pantalla de
planificacion habria mandado a medir 30 casas cuyo diseno no esta aprobado.

Por eso el test que mas importa aqui es el que dice que 'design_pending' NO
genera visita.
"""
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indigo_visits")
class TestIndigoVisits(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Order = cls.env["indigo.order"]
        cls.Stage = cls.env["indigo.stage"]
        cls.dealer = cls.env["res.partner"].create({
            "name": "Visits Test Dealer",
            "is_company": True,
            "is_indigo_dealer": True,
            "email": "visitsdealer@test.example",
        })
        cls.design = cls.env["indigo.design"].create({
            "code": "VISITTEST-SD", "name": "Visit Test Single", "door_type": "SD",
        })

    def _stage(self, code):
        stage = self.Stage.search([("code", "=", code)], limit=1)
        self.assertTrue(stage, "falta la etapa '%s' en los datos base" % code)
        return stage

    def _order(self, stage_code, **vals):
        order = self.Order.create(dict({
            "dealer_id": self.dealer.id,
            "client_name": "Visit Test Client",
            "client_address": "1200 Brickell Ave, Miami, FL 33131",
            "line_ids": [(0, 0, {
                "design_id": self.design.id, "door_type": "SD",
                "color": "white", "width": 36.0, "height": 80.0,
                "qty": 1, "sqf": 20.0,
            })],
        }, **vals))
        order.stage_id = self._stage(stage_code).id
        return order

    # ---------- Lo que SI pide un viaje ----------

    def test_measure_pending_pide_medicion(self):
        order = self._order("measure_pending")
        self.assertEqual(order.visit_type, "measure")

    def test_ready_install_pide_instalacion(self):
        order = self._order("ready_install")
        self.assertEqual(order.visit_type, "install")

    def test_install_scheduled_sigue_pidiendo_instalacion(self):
        # Programada no es lo mismo que hecha: sigue habiendo que conducir,
        # y tiene que seguir contando en la ruta del dia.
        order = self._order("install_scheduled")
        self.assertEqual(order.visit_type, "install")

    # ---------- Lo que NO pide un viaje ----------

    def test_design_pending_no_pide_visita(self):
        """El error que motivo este test.

        Una orden esperando confirmacion de diseno NO espera a nadie con un
        metro: espera al cliente. Si apareciera en la lista de visitas, el
        planificador saldria a medir casas cuyo diseno aun puede cambiar.
        """
        order = self._order("design_pending")
        self.assertFalse(
            order.visit_type,
            "design_pending no puede generar visita: espera al cliente, no al medidor",
        )

    def test_etapas_de_taller_no_piden_visita(self):
        # CNC y pintura ocurren DENTRO del taller. Nadie conduce a ningun sitio.
        for code in ("cnc", "painting", "ready_digitalization"):
            with self.subTest(code=code):
                self.assertFalse(self._order(code).visit_type)

    def test_instalada_ya_no_pide_visita(self):
        order = self._order("installed")
        self.assertFalse(order.visit_type, "ya se fue y se instalo")

    # ---------- La fecha que corresponde a cada clase ----------

    def test_la_fecha_sigue_al_tipo_de_visita(self):
        """visit_date tiene que tomar la fecha de SU clase de visita.

        Las dos fechas conviven en la misma orden -- primero se mide y luego
        se instala -- asi que mezclarlas pondria una instalacion en la lista
        del dia en que solo tocaba medir.
        """
        order = self._order(
            "measure_pending",
            measurement_date="2026-03-10",
            installation_date="2026-04-20",
        )
        self.assertEqual(str(order.visit_date), "2026-03-10")

        order.stage_id = self._stage("ready_install").id
        self.assertEqual(
            str(order.visit_date), "2026-04-20",
            "al pasar a instalar, la fecha de la visita es la de instalacion",
        )

    def test_sin_fecha_la_visita_sigue_existiendo(self):
        # Una visita sin programar es justo la que hay que encontrar; si
        # visit_type se apagara sin fecha, desapareceria de la pantalla.
        order = self._order("ready_install")
        self.assertEqual(order.visit_type, "install")
        self.assertFalse(order.visit_date)

    # ---------- Comportamiento deliberado ----------

    def test_en_espera_no_esconde_la_visita(self):
        """Una orden pospuesta sigue estando en su sitio y a su distancia.

        Apagarla aqui impediria ver "tengo tres paradas en el norte, una de
        ellas en espera". Quien decide si se muestra es el filtro de la vista,
        no el campo.
        """
        order = self._order("ready_install")
        # hold_cause es obligatorio al poner una orden en espera
        # (_check_hold_requires_cause): sin causa no se puede contar ni
        # distinguir quien tiene que desbloquearla.
        order.write({"on_hold": True, "hold_cause": "client"})
        self.assertEqual(order.visit_type, "install")

    def test_cambiar_de_etapa_recalcula(self):
        order = self._order("measure_pending")
        self.assertEqual(order.visit_type, "measure")
        order.stage_id = self._stage("cnc").id
        self.assertFalse(order.visit_type, "en CNC ya no hay nada que visitar")
        order.stage_id = self._stage("ready_install").id
        self.assertEqual(order.visit_type, "install")

    # ---------- Lo que hace util la pantalla ----------

    def test_la_geo_ya_esta_para_las_de_medicion(self):
        """El corredor no depende de la etapa, y ese es el punto entero.

        Se calcula desde el ZIP en cuanto hay direccion, asi que una orden que
        espera medicion ya sabe hacia donde cae. Si esto dejara de cumplirse,
        agrupar por corredor solo funcionaria para instalaciones y la pantalla
        perderia su razon de ser.
        """
        order = self._order("measure_pending")
        self.assertTrue(
            order.install_corridor,
            "una orden a medir tiene que tener corredor igual que una a instalar",
        )
        self.assertGreater(order.install_distance_mi, 0.0)
