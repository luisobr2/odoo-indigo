# -*- coding: utf-8 -*-
"""Distancia y lado para planificar instalaciones (pedido de Majela, 2026-08-15).

Lo que se prueba no es "la formula da un numero" sino las tres cosas de las
que depende una decision de ruta: que la distancia sea creible contra
lugares que el taller conoce, que el lado no mienta, y que un dato faltante
se vea como faltante y no como "al lado del taller".
"""
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.indigo_decors.models.indigo_zip_geo import (
    corridor_from_coords,
    haversine_miles,
)


@tagged("post_install", "-at_install", "indigo_geo")
class TestIndigoInstallGeo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Order = cls.env["indigo.order"]
        cls.Design = cls.env["indigo.design"]
        cls.Range = cls.env["indigo.install.range"]
        cls.Geo = cls.env["indigo.zip.geo"]
        cls.dealer = cls.env["res.partner"].create({
            "name": "Geo Test Dealer",
            "is_company": True,
            "is_indigo_dealer": True,
            "email": "geodealer@test.example",
        })
        cls.design = cls.Design.create({
            "code": "GEOTEST-SD", "name": "Geo Test Single", "door_type": "SD",
        })

    def _order(self, address):
        return self.Order.create({
            "dealer_id": self.dealer.id,
            "client_name": "Geo Test Client",
            "client_address": address,
            "line_ids": [(0, 0, {
                "design_id": self.design.id, "door_type": "SD",
                "color": "white", "width": 36.0, "height": 80.0,
                "qty": 1, "sqf": 20.0,
            })],
        })

    # ---------- Los datos base ----------

    def test_florida_zips_are_loaded(self):
        # Sin la tabla cargada, todo lo demas da "sin clasificar" en silencio.
        self.assertGreater(
            self.Geo.search_count([]), 900,
            "Deben estar cargados los ZIP de Florida (data/indigo.zip.geo.csv)",
        )
        self.assertTrue(self.Geo.coords_for_zip("33138"), "falta el ZIP del taller")

    def test_ranges_are_seeded_and_contiguous(self):
        ranges = self.Range.search([], order="sequence")
        self.assertEqual(len(ranges), 5, "los 5 rangos del mockup de Majela")
        # Sin huecos ni solapes: el limite superior de uno es el inferior del
        # siguiente. Un hueco dejaria ordenes sin rango por un redondeo.
        for prev, nxt in zip(ranges, ranges[1:]):
            self.assertEqual(
                prev.max_miles, nxt.min_miles,
                "hueco o solape entre '%s' y '%s'" % (prev.name, nxt.name),
            )
        self.assertFalse(ranges[-1].max_miles, "el ultimo rango no lleva tope")

    # ---------- Distancias creibles ----------

    def test_known_places_land_in_the_right_range(self):
        # Distancias reales de manejo desde el taller (Little River, Miami),
        # verificadas contra lugares que el taller visita todas las semanas.
        casos = [
            ("Miami Beach",     "1200 Ocean Dr, Miami Beach, FL 33139",        0, 35),
            ("Hollywood",       "6900 SW 9th St Hollywood, FL 33023",          0, 35),
            ("Palmetto Bay",    "18561 SW 94th AVE, CUTLER BAY, FL 33157",     0, 35),
            ("Parkland",        "7669 NW 117th Ln PARKLAND, FL 33076",        35, 45),
            ("Delray Beach",    "7788 Edinburough Ln, Delray Beach, FL 33446", 45, 90),
            ("Port St. Lucie",  "3917 SW Laidlow St Port Saint Lucie, FL 34953", 120, 999),
        ]
        for lugar, direccion, lo, hi in casos:
            order = self._order(direccion)
            self.assertTrue(order.install_range_id, "%s quedo sin rango" % lugar)
            self.assertGreaterEqual(order.install_distance_mi, lo, lugar)
            self.assertLess(order.install_distance_mi, hi, lugar)

    def test_north_and_south_are_not_confused(self):
        # El motivo entero del pedido: "35 millas para el norte no es
        # compatible con 35 millas para el SUR".
        norte = self._order("7669 NW 117th Ln PARKLAND, FL 33076")
        sur = self._order("18561 SW 94th AVE, CUTLER BAY, FL 33157")
        self.assertEqual(norte.install_corridor, "N", "Parkland sube por la Turnpike")
        self.assertEqual(sur.install_corridor, "S", "Cutler Bay baja a south Dade")

    def test_the_west_coast_is_not_the_same_trip_as_doral(self):
        # El caso que hundio al rumbo geometrico: los dos caen "al oeste", uno
        # esta a 17 millas y el otro a 140 cruzando los Everglades.
        doral = self._order("8400 NW 36th St, Doral, FL 33178")
        fmyers = self._order("13401 Summerlin Rd, Fort Myers, FL 33919")
        self.assertNotEqual(
            doral.install_corridor, fmyers.install_corridor,
            "Doral y Fort Myers no pueden compartir corredor",
        )
        self.assertEqual(fmyers.install_corridor, "SW")

    def test_corridors_match_the_examples_the_client_gave(self):
        # La verdad de referencia son los ejemplos que dio Majela el
        # 2026-08-19. Si esto se rompe, la tabla de ZIPs dejo de coincidir con
        # como el taller entiende su propio mapa.
        casos = [
            ("33157", "S",  "Cutler Bay"),
            ("33030", "S",  "Homestead"),
            ("33040", "S",  "Key West: al oeste en longitud, pero viaje al sur"),
            ("33139", "C",  "Miami Beach"),
            ("33014", "C",  "Hialeah"),
            ("33178", "W",  "Doral"),
            ("33326", "W",  "Weston"),
            ("33301", "N",  "Fort Lauderdale"),
            ("33401", "N",  "West Palm Beach"),
            ("34145", "SW", "Marco Island"),
            ("33904", "SW", "Cape Coral"),
        ]
        for zc, esperado, lugar in casos:
            rec = self.Geo.search([("zip", "=", zc)], limit=1)
            self.assertTrue(rec, "falta el ZIP %s (%s)" % (zc, lugar))
            self.assertEqual(rec.corridor, esperado, "%s (%s)" % (lugar, zc))

    def test_zip_comes_from_the_end_not_the_street_number(self):
        # "10911 NW 38th Ct Coral Springs, FL 33065": el primer grupo de 5
        # digitos es el numero de la calle. Tomarlo mandaria la orden a
        # cualquier lado -- de hecho 10911 ni siquiera es un ZIP de Florida.
        order = self._order("10911 NW 38th Ct Coral Springs, FL 33065")
        self.assertEqual(order.client_zip, "33065")
        self.assertTrue(order.install_range_id)
        self.assertEqual(order.install_corridor, "N")

    def test_zip_is_found_even_when_the_state_is_glued_to_it(self):
        # Caso real de produccion (IND/2026/00078). Con el limite de palabra
        # que habia antes, "FL33028" no exponia el codigo postal y el parser
        # se quedaba con 17042 -- el numero de la calle -- dejando la orden
        # con un ZIP de Pennsylvania y sin corredor.
        order = self._order("17042 NW 10th ST PEMBROKE PINES FL33028")
        self.assertEqual(order.client_zip, "33028", "el ZIP va al final, no al principio")
        self.assertTrue(order.install_range_id)
        self.assertIn(order.install_corridor, ("N", "W"))

    def test_a_phone_number_is_not_mistaken_for_a_zip(self):
        # La contracara de quitar los limites de palabra: no puede agarrar 5
        # cifras del medio de un numero mas largo.
        order = self._order("Tel 3055551234, 900 Brickell Ave Miami FL 33131")
        self.assertEqual(order.client_zip, "33131")

    def test_backfill_fixes_a_stored_zip_that_contradicts_the_address(self):
        # El backfill corrige, no solo rellena: un ZIP guardado que no
        # coincide con la direccion casi siempre es un parseo viejo malo.
        order = self._order("7669 NW 117th Ln PARKLAND, FL 33076")
        order.client_zip = "17042"          # como quedo por el bug
        order.invalidate_recordset(["install_corridor"])
        cambios = self.Order.indigo_backfill_client_zip()
        self.assertTrue(any(c[0] == order.name for c in cambios))
        self.assertEqual(order.client_zip, "33076")

    def test_backfill_leaves_alone_an_order_whose_address_has_no_zip(self):
        # No se puede inventar: sin codigo postal en el texto, se deja como esta.
        order = self._order("Traen la puerta aqui")
        self.assertFalse(order.client_zip)
        self.Order.indigo_backfill_client_zip()
        self.assertFalse(order.client_zip)

    # ---------- Lo que falta, se ve que falta ----------

    def test_unknown_zip_is_blank_not_zero(self):
        # Una orden sin dato y una orden al lado del taller no pueden verse
        # igual en un tablero que se usa para decidir viajes.
        order = self._order("Somewhere with no postal code at all")
        self.assertFalse(order.client_zip)
        self.assertFalse(order.install_range_id)
        self.assertFalse(order.install_corridor)
        self.assertEqual(order.install_distance_mi, 0.0)

    def test_out_of_state_zip_without_coords_is_blank(self):
        # 17042 es de Pennsylvania: ni el ZIP ni su prefijo 170 estan en la
        # tabla de Florida, asi que ni siquiera el respaldo lo alcanza.
        order = self._order("100 Main St, Lebanon, PA 17042")
        self.assertEqual(order.client_zip, "17042")
        self.assertFalse(order.install_range_id, "un ZIP sin coordenadas no tiene rango")

    def test_non_zcta_zip_falls_back_to_the_prefix(self):
        # El censo publica ZCTA, no ZIPs: los de solo apartado postal no
        # existen como area. 33336 son los apartados de Fort Lauderdale y en
        # produccion hay ordenes reales con el. Sin respaldo aparecerian "sin
        # ubicar", cuando cualquiera sabe que Fort Lauderdale esta al norte.
        self.assertFalse(self.Geo.search([("zip", "=", "33336")]), "premisa: 33336 no es ZCTA")
        order = self._order("PO Box 123, Fort Lauderdale, FL 33336")
        self.assertEqual(order.client_zip, "33336")
        self.assertTrue(order.install_range_id, "el prefijo 333 tiene que ubicarla")
        self.assertTrue(order.install_geo_approx, "y tiene que quedar marcada como aproximada")

    def test_exact_zip_is_not_flagged_as_approximate(self):
        order = self._order("7669 NW 117th Ln PARKLAND, FL 33076")
        self.assertTrue(order.install_range_id)
        self.assertFalse(order.install_geo_approx)

    def test_recompute_includes_archived_orders(self):
        # search([]) las salta por defecto. Saltarlas en silencio hace que los
        # totales no cierren y que nadie entienda por que.
        order = self._order("6900 SW 9th St Hollywood, FL 33023")
        order.active = False
        order.invalidate_recordset(["install_range_id"])
        self.Order.indigo_recompute_install_geo()
        self.assertTrue(
            order.with_context(active_test=False).install_range_id,
            "una orden archivada tambien tiene que recalcularse",
        )

    def test_editing_the_address_reclassifies_the_order(self):
        order = self._order("18561 SW 94th AVE, CUTLER BAY, FL 33157")
        self.assertEqual(order.install_corridor, "S")
        order.write({"client_address": "7669 NW 117th Ln PARKLAND, FL 33076",
                     "client_zip": "33076"})
        self.assertEqual(order.install_corridor, "N",
                         "al corregir la direccion tiene que recalcularse")

    def test_fixing_a_zip_corridor_reclassifies_its_orders(self):
        # La valvula de escape: si un ZIP quedo en el corredor equivocado, se
        # corrige una vez y todas sus ordenes se acomodan.
        order = self._order("7669 NW 117th Ln PARKLAND, FL 33076")
        self.assertEqual(order.install_corridor, "N")
        self.Geo.search([("zip", "=", "33076")], limit=1).corridor = "W"
        self.Order.indigo_recompute_install_geo()
        self.assertEqual(order.install_corridor, "W")

    # ---------- Los limites de los rangos ----------

    def test_range_upper_bound_is_exclusive(self):
        # 35.0 exactas caen en 35-45, no en 0-35: si el tope fuera inclusivo,
        # los rangos contiguos se solaparian y la misma orden contaria dos veces.
        local = self.env.ref("indigo_decors.install_range_local")
        near = self.env.ref("indigo_decors.install_range_near")
        self.assertEqual(self.Range.range_for_miles(34.9), local)
        self.assertEqual(self.Range.range_for_miles(35.0), near)

    def test_range_rejects_inverted_bounds(self):
        with self.assertRaises(ValidationError):
            self.Range.create({"name": "Al reves", "min_miles": 50, "max_miles": 10})

    # ---------- Las funciones puras ----------

    def test_haversine_against_a_known_distance(self):
        # Miami -> Orlando, 205 millas en linea recta (la de manejar son
        # ~235; la diferencia es justo el rodeo que corrige el factor).
        d = haversine_miles(25.7617, -80.1918, 28.5383, -81.3792)
        self.assertAlmostEqual(d, 205.3, delta=2.0)

    def test_the_seeding_rule_never_returns_an_unknown_corridor(self):
        # Barrido grueso del sur de Florida: ningun punto puede quedar fuera
        # de los 5 corredores, o habria ordenes sin clasificar sin motivo.
        validos = {"S", "C", "W", "N", "SW"}
        for lat10 in range(244, 290):
            for lon10 in range(-822, -799):
                self.assertIn(corridor_from_coords(lat10 / 10.0, lon10 / 10.0), validos)

    def test_recompute_helper_touches_every_order(self):
        self._order("6900 SW 9th St Hollywood, FL 33023")
        n = self.Order.indigo_recompute_install_geo()
        self.assertGreater(n, 0)
