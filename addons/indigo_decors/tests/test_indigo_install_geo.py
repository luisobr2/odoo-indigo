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
    bearing_degrees,
    compass_from_bearing,
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
        # El motivo entero del pedido: "no voy a mandar al sur y al norte el
        # mismo dia". Si el lado se equivoca, la pantalla es peor que nada.
        norte = self._order("7669 NW 117th Ln PARKLAND, FL 33076")
        sur = self._order("18561 SW 94th AVE, CUTLER BAY, FL 33157")
        self.assertIn(norte.install_direction, ("N", "NE", "NO"), "Parkland esta al norte")
        self.assertIn(sur.install_direction, ("S", "SE", "SO"), "Cutler Bay esta al sur")

    def test_zip_comes_from_the_end_not_the_street_number(self):
        # "10911 NW 38th Ct Coral Springs, FL 33065": el primer grupo de 5
        # digitos es el numero de la calle. Tomarlo mandaria la orden a
        # cualquier lado -- de hecho 10911 ni siquiera es un ZIP de Florida.
        order = self._order("10911 NW 38th Ct Coral Springs, FL 33065")
        self.assertEqual(order.client_zip, "33065")
        self.assertTrue(order.install_range_id)
        self.assertIn(order.install_direction, ("N", "NO", "NE"))

    # ---------- Lo que falta, se ve que falta ----------

    def test_unknown_zip_is_blank_not_zero(self):
        # Una orden sin dato y una orden al lado del taller no pueden verse
        # igual en un tablero que se usa para decidir viajes.
        order = self._order("Somewhere with no postal code at all")
        self.assertFalse(order.client_zip)
        self.assertFalse(order.install_range_id)
        self.assertFalse(order.install_direction)
        self.assertEqual(order.install_distance_mi, 0.0)

    def test_out_of_state_zip_without_coords_is_blank(self):
        # 17042 es de Pennsylvania: no esta en la tabla de Florida. Debe
        # quedar sin clasificar, no caer en el rango local.
        order = self._order("100 Main St, Lebanon, PA 17042")
        self.assertEqual(order.client_zip, "17042")
        self.assertFalse(order.install_range_id, "un ZIP sin coordenadas no tiene rango")

    def test_editing_the_address_reclassifies_the_order(self):
        order = self._order("18561 SW 94th AVE, CUTLER BAY, FL 33157")
        self.assertIn(order.install_direction, ("S", "SE", "SO"))
        order.write({"client_address": "7669 NW 117th Ln PARKLAND, FL 33076",
                     "client_zip": "33076"})
        self.assertIn(order.install_direction, ("N", "NE", "NO"),
                      "al corregir la direccion tiene que recalcularse")

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

    def test_bearing_and_compass_agree_with_the_map(self):
        # Desde el taller, derecho al norte y derecho al sur.
        self.assertEqual(compass_from_bearing(bearing_degrees(25.85, -80.18, 26.85, -80.18)), "N")
        self.assertEqual(compass_from_bearing(bearing_degrees(25.85, -80.18, 24.85, -80.18)), "S")
        # Los 8 sectores cubren la rosa completa sin huecos.
        vistos = {compass_from_bearing(g) for g in range(0, 360, 5)}
        self.assertEqual(len(vistos), 8)

    def test_recompute_helper_touches_every_order(self):
        self._order("6900 SW 9th St Hollywood, FL 33023")
        n = self.Order.indigo_recompute_install_geo()
        self.assertGreater(n, 0)
