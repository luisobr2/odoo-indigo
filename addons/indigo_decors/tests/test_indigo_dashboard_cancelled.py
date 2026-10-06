# -*- coding: utf-8 -*-
"""Una orden cancelada no cuenta como trabajo vivo en el dashboard.

Cancelar no mueve la etapa (queda `cancelled_at`), asi que la orden seguia
contando en «New Order» y en las ordenes activas (Majela, 6-oct-2026: la
00432 estaba cancelada y aparecia como New Order).
"""
from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestIndigoDashboardCancelled(TransactionCase):
    def test_cancelled_order_leaves_the_counts(self):
        dealer = self.env["res.partner"].create({"name": "Dash Dealer", "is_indigo_dealer": True})
        order = self.env["indigo.order"].create({"dealer_id": dealer.id, "client_name": "Dash Client"})
        Order = self.env["indigo.order"]

        def new_count(data):
            return next((p["count"] for p in data["pipeline"] if p["code"] == "new"), 0)

        before = Order.get_dashboard_data()
        order.cancelled_at = fields.Datetime.now()
        after = Order.get_dashboard_data()
        self.assertEqual(after["kpis"]["active_count"], before["kpis"]["active_count"] - 1)
        self.assertEqual(new_count(after), new_count(before) - 1)
