# -*- coding: utf-8 -*-
"""El pago al instalador se calcula por DIA, no por orden.

Lo que dijo Majela por WhatsApp el 2026-08-21, textual:

    "Por dia son 150"
    "Mandy siempre es 150 x dia mas 10 por cada instalacion que
     corresponde a gasolina y tolls"
    "Lazaro 150 si las puertas suman menos que eso. Cada puerta es 35"

O sea dos acuerdos distintos que entran en una sola formula:

    pago del dia = max(minimo_diario, tarifa_puerta * puertas)
                 + bono * instalaciones

  Mandy:  minimo 150, tarifa_puerta 0,  bono 10  -> 150 + 10*instalaciones
  Lazaro: minimo 150, tarifa_puerta 35, bono 0   -> max(150, 35*puertas)

Mandy no cobra por puerta, asi que su tarifa por puerta es 0 y el minimo
es siempre su piso. Los tres numeros se editan desde el panel; aqui no
hay ninguno hardcodeado.

Por que importa: el sistema venia pagando 35/puerta plano, sin minimo.
Medido en produccion, 49 de 53 dias de trabajo tuvieron 4 puertas o
menos -- por debajo del minimo -- asi que la regla vieja se equivocaba
el 92% de los dias.
"""
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestInstallerDayPay(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Order = cls.env["indigo.order"]
        cls.Payout = cls.env["indigo.payout"]
        cls.Rate = cls.env["indigo.contractor.rate"]
        cls.Design = cls.env["indigo.design"]

        cls.dealer = cls.Partner.create({
            "name": "Day Pay Dealer", "is_company": True, "is_indigo_dealer": True,
        })
        cls.design = cls.Design.create({
            "code": "DAYPAY-SD", "name": "Day Pay Single", "door_type": "SD",
        })
        cls.mandy = cls.Partner.create({"name": "Mandy DayPay"})
        cls.lazaro = cls.Partner.create({"name": "Lazaro DayPay"})
        cls.nobody = cls.Partner.create({"name": "Sin regla propia"})

        cls.stage_scheduled = cls.env.ref("indigo_decors.stage_install_scheduled")
        cls.stage_installed = cls.env.ref("indigo_decors.stage_installed")

        # Reglas: una por instalador, mas la de por defecto (sin partner).
        cls.Rate.search([("contractor_type", "=", "installer")]).write({"active": False})
        cls.rule_default = cls.Rate.create({
            "name": "Instalador - por defecto",
            "contractor_type": "installer",
            "rate": 35.0, "rate_unit": "piece",
            "daily_minimum": 150.0, "bonus_amount": 0.0,
        })
        cls.rule_mandy = cls.Rate.create({
            "name": "Mandy", "contractor_type": "installer", "partner_id": cls.mandy.id,
            "rate": 0.0, "rate_unit": "piece",
            "daily_minimum": 150.0, "bonus_amount": 10.0, "bonus_unit": "order",
        })
        cls.rule_lazaro = cls.Rate.create({
            "name": "Lazaro", "contractor_type": "installer", "partner_id": cls.lazaro.id,
            "rate": 35.0, "rate_unit": "piece",
            "daily_minimum": 150.0, "bonus_amount": 0.0,
        })

    def _install(self, installer, doors, day, **extra):
        """Crea una orden con `doors` puertas y la marca instalada el dia `day`."""
        order = self.Order.create(dict({
            "dealer_id": self.dealer.id,
            "client_name": "Cliente %s" % doors,
            "installer_ids": [(6, 0, [installer.id])],
            "installation_date": day,
            "stage_id": self.stage_scheduled.id,
            "line_ids": [(0, 0, {
                "design_id": self.design.id, "door_type": "SD",
                "color": "white", "qty": doors, "sqf": 20.0,
            })],
        }, **extra))
        order.stage_id = self.stage_installed
        return order

    def _day_total(self, installer, day):
        payouts = self.Payout.search([
            ("contractor_id", "=", installer.id),
            ("contractor_type", "=", "installer"),
            ("work_date", "=", day),
            ("state", "!=", "cancel"),
        ])
        self.assertEqual(len(payouts), 1,
                         "debe haber exactamente UNA liquidacion por instalador y dia")
        return payouts.amount, payouts

    # ---------------- la regla de Lazaro: piso de 150 ----------------

    def test_lazaro_un_dia_flojo_cobra_el_minimo(self):
        # 2 puertas * 35 = 70, por debajo del minimo -> 150.
        self._install(self.lazaro, 2, "2026-09-01")
        total, _ = self._day_total(self.lazaro, "2026-09-01")
        self.assertAlmostEqual(total, 150.0, 2)

    def test_lazaro_cuatro_puertas_todavia_cobra_el_minimo(self):
        # 4 * 35 = 140 < 150. El corte real esta en 5 puertas, no en 2
        # como decia el mockup.
        self._install(self.lazaro, 4, "2026-09-02")
        total, _ = self._day_total(self.lazaro, "2026-09-02")
        self.assertAlmostEqual(total, 150.0, 2)

    def test_lazaro_cinco_puertas_ya_cobra_por_puerta(self):
        self._install(self.lazaro, 5, "2026-09-03")
        total, _ = self._day_total(self.lazaro, "2026-09-03")
        self.assertAlmostEqual(total, 175.0, 2)

    def test_lazaro_varias_ordenes_el_mismo_dia_suman_UNA_liquidacion(self):
        # Esto es lo que la regla vieja no podia hacer: el minimo se aplica
        # al dia entero, no a cada orden. Tres ordenes de 2 puertas =
        # 6 puertas = 210, no tres minimos de 150.
        self._install(self.lazaro, 2, "2026-09-04")
        self._install(self.lazaro, 2, "2026-09-04")
        self._install(self.lazaro, 2, "2026-09-04")
        total, payout = self._day_total(self.lazaro, "2026-09-04")
        self.assertAlmostEqual(total, 210.0, 2)
        self.assertEqual(len(payout.line_ids.filtered(lambda l: l.line_kind == "work")), 3)

    def test_dias_distintos_son_liquidaciones_distintas(self):
        self._install(self.lazaro, 1, "2026-09-05")
        self._install(self.lazaro, 1, "2026-09-06")
        self.assertAlmostEqual(self._day_total(self.lazaro, "2026-09-05")[0], 150.0, 2)
        self.assertAlmostEqual(self._day_total(self.lazaro, "2026-09-06")[0], 150.0, 2)

    # ---------------- la regla de Mandy: diario + bono ----------------

    def test_mandy_cobra_diario_mas_bono_por_instalacion(self):
        # 150 + 10 = 160, sin importar cuantas puertas trae la orden.
        self._install(self.mandy, 3, "2026-09-07")
        total, _ = self._day_total(self.mandy, "2026-09-07")
        self.assertAlmostEqual(total, 160.0, 2)

    def test_mandy_dos_instalaciones_dos_bonos(self):
        self._install(self.mandy, 1, "2026-09-08")
        self._install(self.mandy, 4, "2026-09-08")
        total, _ = self._day_total(self.mandy, "2026-09-08")
        self.assertAlmostEqual(total, 170.0, 2)

    def test_mandy_no_cobra_por_puerta(self):
        # Muchas puertas no le mueven el pago: su tarifa por puerta es 0.
        self._install(self.mandy, 12, "2026-09-09")
        total, _ = self._day_total(self.mandy, "2026-09-09")
        self.assertAlmostEqual(total, 160.0, 2)

    # ---------------- configurabilidad ----------------

    def test_un_instalador_sin_regla_propia_usa_la_de_por_defecto(self):
        self._install(self.nobody, 2, "2026-09-10")
        total, _ = self._day_total(self.nobody, "2026-09-10")
        self.assertAlmostEqual(total, 150.0, 2)

    def test_cambiar_el_minimo_en_la_config_cambia_lo_que_se_paga(self):
        # Nada esta hardcodeado: subir el minimo desde el panel se refleja.
        self.rule_lazaro.daily_minimum = 200.0
        self._install(self.lazaro, 2, "2026-09-11")
        total, _ = self._day_total(self.lazaro, "2026-09-11")
        self.assertAlmostEqual(total, 200.0, 2)

    def test_el_bono_puede_pagarse_por_puerta_en_vez_de_por_orden(self):
        # "10 por cada instalacion" era ambiguo; la unidad es configurable.
        self.rule_mandy.bonus_unit = "door"
        self._install(self.mandy, 3, "2026-09-12")
        total, _ = self._day_total(self.mandy, "2026-09-12")
        self.assertAlmostEqual(total, 180.0, 2)  # 150 + 3*10

    # ---------------- trazabilidad y seguridad ----------------

    def test_el_ajuste_al_minimo_queda_como_renglon_visible(self):
        # Majela tiene que poder explicarle el total al instalador: se ven
        # las puertas y se ve el ajuste, no un numero magico.
        self._install(self.lazaro, 2, "2026-09-13")
        _, payout = self._day_total(self.lazaro, "2026-09-13")
        work = payout.line_ids.filtered(lambda l: l.line_kind == "work")
        adj = payout.line_ids.filtered(lambda l: l.line_kind == "minimum")
        self.assertAlmostEqual(sum(work.mapped("amount")), 70.0, 2)
        self.assertEqual(len(adj), 1)
        self.assertAlmostEqual(adj.amount, 80.0, 2, "70 + 80 = el minimo de 150")

    def test_sin_ajuste_cuando_el_dia_supera_el_minimo(self):
        self._install(self.lazaro, 6, "2026-09-14")
        _, payout = self._day_total(self.lazaro, "2026-09-14")
        self.assertFalse(payout.line_ids.filtered(lambda l: l.line_kind == "minimum"))
        self.assertAlmostEqual(payout.amount, 210.0, 2)

    def test_una_liquidacion_ya_pagada_no_se_recalcula(self):
        # Reabrir el dia y reescribir plata ya entregada seria inaceptable:
        # la orden nueva se contabiliza aparte.
        self._install(self.lazaro, 2, "2026-09-15")
        _, payout = self._day_total(self.lazaro, "2026-09-15")
        payout.action_mark_paid()
        antes = payout.amount
        self._install(self.lazaro, 5, "2026-09-15")
        self.assertAlmostEqual(payout.amount, antes, 2,
                               "la liquidacion pagada quedo intacta")
        abiertas = self.Payout.search([
            ("contractor_id", "=", self.lazaro.id),
            ("work_date", "=", "2026-09-15"),
            ("state", "=", "draft"),
        ])
        self.assertEqual(len(abiertas), 1, "el trabajo nuevo va a una liquidacion aparte")

    def test_reprocesar_la_misma_orden_no_duplica_el_renglon(self):
        order = self._install(self.lazaro, 3, "2026-09-16")
        order._create_installer_payouts()
        order._create_installer_payouts()
        _, payout = self._day_total(self.lazaro, "2026-09-16")
        self.assertEqual(len(payout.line_ids.filtered(lambda l: l.line_kind == "work")), 1)
        self.assertAlmostEqual(payout.amount, 150.0, 2)

    def test_dos_instaladores_el_mismo_dia_cobran_cada_uno_su_regla(self):
        self._install(self.lazaro, 2, "2026-09-17")
        self._install(self.mandy, 2, "2026-09-17")
        self.assertAlmostEqual(self._day_total(self.lazaro, "2026-09-17")[0], 150.0, 2)
        self.assertAlmostEqual(self._day_total(self.mandy, "2026-09-17")[0], 160.0, 2)

    # ---------------- consolidacion de lo viejo ----------------

    def _legacy_payout(self, installer, day, doors, rate=35.0):
        """Reproduce la forma vieja: UNA liquidacion por orden, sin dia."""
        order = self.Order.create({
            "dealer_id": self.dealer.id, "client_name": "Legacy",
            "installer_ids": [(6, 0, [installer.id])],
            "installation_date": day,
            "line_ids": [(0, 0, {
                "design_id": self.design.id, "door_type": "SD",
                "color": "white", "qty": doors, "sqf": 10.0,
            })],
        })
        payout = self.Payout.create({
            "contractor_id": installer.id, "contractor_type": "installer",
            "work_date": day,
        })
        self.env["indigo.payout.line"].create({
            "payout_id": payout.id, "order_id": order.id, "line_kind": "work",
            "date_work": day, "description": "Instalacion %s" % order.name,
            "quantity": doors, "rate": rate,
        })
        return payout

    def test_el_recalculo_junta_las_liquidaciones_sueltas_de_un_mismo_dia(self):
        # Tres ordenes de 2 puertas el mismo dia, emitidas por separado como
        # hacia el codigo viejo. Sin consolidar, la regla les daria un
        # minimo a cada una: 450 por una jornada de 6 puertas.
        for _i in range(3):
            self._legacy_payout(self.lazaro, "2026-10-01", 2)
        abiertas = self.Payout.search([
            ("contractor_id", "=", self.lazaro.id), ("work_date", "=", "2026-10-01"),
            ("state", "=", "draft"),
        ])
        self.assertEqual(len(abiertas), 3)

        res = self.Payout.indigo_recompute_installer_days("2026-10-01", "2026-10-01")
        self.assertEqual(res["consolidadas"], 2)

        total, payout = self._day_total(self.lazaro, "2026-10-01")
        self.assertAlmostEqual(total, 210.0, 2, "6 puertas * 35, UN solo dia")
        self.assertEqual(len(payout.line_ids.filtered(lambda l: l.line_kind == "work")), 3)

    def test_las_consolidadas_se_cancelan_no_se_borran(self):
        # Son registros de plata: quien mire el historico tiene que poder
        # ver que existieron y por que se cerraron.
        viejas = [self._legacy_payout(self.lazaro, "2026-10-02", 1) for _i in range(2)]
        self.Payout.indigo_recompute_installer_days("2026-10-02", "2026-10-02")
        canceladas = [p for p in viejas if p.state == "cancel"]
        self.assertEqual(len(canceladas), 1)
        self.assertTrue(canceladas[0].exists())
        self.assertIn("Consolidada en", canceladas[0].notes)

    def test_el_recalculo_no_toca_una_jornada_ya_pagada(self):
        pagada = self._legacy_payout(self.lazaro, "2026-10-03", 1)
        pagada.action_mark_paid()
        antes = pagada.amount
        self.Payout.indigo_recompute_installer_days("2026-10-03", "2026-10-03")
        self.assertEqual(pagada.state, "paid")
        self.assertAlmostEqual(pagada.amount, antes, 2)

    def test_el_recalculo_respeta_el_periodo_pedido(self):
        self._legacy_payout(self.lazaro, "2026-10-04", 1)
        fuera = self._legacy_payout(self.lazaro, "2026-11-20", 1)
        antes = fuera.amount
        self.Payout.indigo_recompute_installer_days("2026-10-01", "2026-10-31")
        self.assertAlmostEqual(fuera.amount, antes, 2, "quedo fuera del periodo")
        self.assertAlmostEqual(self._day_total(self.lazaro, "2026-10-04")[0], 150.0, 2)

    def test_una_orden_compartida_reparte_las_puertas(self):
        # Dos instaladores en la misma orden: cada uno su mitad de puertas,
        # y cada uno su propio minimo.
        self._install(self.lazaro, 6, "2026-09-18",
                      installer_ids=[(6, 0, [self.lazaro.id, self.mandy.id])])
        total_l, payout_l = self._day_total(self.lazaro, "2026-09-18")
        work = payout_l.line_ids.filtered(lambda l: l.line_kind == "work")
        self.assertAlmostEqual(sum(work.mapped("quantity")), 3.0, 2)
        self.assertAlmostEqual(total_l, 150.0, 2)  # 3*35=105 -> sube al minimo
