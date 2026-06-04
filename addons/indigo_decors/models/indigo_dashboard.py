# -*- coding: utf-8 -*-
"""Backend method for the Indigo Dashboard client action.

All the dashboard's KPIs and panels in ONE roundtrip to the server so
the OWL component can render without a chain of waterfall RPCs.
"""
from datetime import timedelta

from odoo import api, fields, models


# Stage codes used across the dashboard. Kept in one place so the
# pipeline preview, KPI windows, and dealer breakdown stay in sync.
PIPELINE_PREVIEW_CODES = [
    "new",
    "measure_pending",
    "ready_digitalization",
    "cnc",
    "painting",
    "install_scheduled",
]
CLOSED_CODES = ("closed", "invoiced")
PENDING_INSTALL_CODES = ("ready_install", "install_scheduled")


class IndigoOrderDashboard(models.Model):
    _inherit = "indigo.order"

    @api.model
    def get_dashboard_data(self):
        """Return all dashboard panels in a single dict.

        Shape:
          {
            kpis: { active_count, created_week, pending_install, revenue_month },
            dealers: [ { id, name, count, in_painting, ready_install,
                         total_sqf, pending_revenue } ],
            pipeline: [ { code, name, count, oldest } ],
            today_installs: [ { installer_name, orders: [...] } ],
            health: { overdue_count, avg_aging, week_due, week_installed },
            generated_at: <iso datetime string>,
          }
        """
        today = fields.Date.context_today(self)
        week_ago = today - timedelta(days=7)
        month_start = today.replace(day=1)
        Order = self.env["indigo.order"]

        # ---------- Top KPIs ----------
        active_count = Order.search_count(
            [("stage_id.code", "not in", list(CLOSED_CODES))]
        )
        created_week = Order.search_count(
            [("create_date", ">=", fields.Datetime.to_string(
                fields.Datetime.now() - timedelta(days=7)
            ))]
        )
        pending_install = Order.search_count(
            [("stage_id.code", "in", list(PENDING_INSTALL_CODES))]
        )
        # Revenue this month: anchored on date_paid (set when payment_state
        # flips to 'paid'). Falls back to today for legacy paid orders that
        # were marked before this field existed.
        paid_orders = Order.search(
            [
                ("payment_state", "=", "paid"),
                ("date_paid", ">=", fields.Date.to_string(month_start)),
            ]
        )
        revenue_month = sum(paid_orders.mapped("total_dealer_charge"))

        # ---------- Orders by Dealer ----------
        # Only show dealers that actually have active orders -> mockup auto-grows.
        active_orders = Order.search(
            [("stage_id.code", "not in", list(CLOSED_CODES))]
        )
        dealer_buckets = {}
        for o in active_orders:
            d = o.dealer_id
            if not d:
                continue
            b = dealer_buckets.setdefault(d.id, {
                "id": d.id,
                "name": d.name,
                "count": 0,
                "in_painting": 0,
                "ready_install": 0,
                "total_sqf": 0.0,
                "pending_revenue": 0.0,
            })
            b["count"] += 1
            code = o.stage_id.code or ""
            if code == "painting":
                b["in_painting"] += 1
            if code in PENDING_INSTALL_CODES:
                b["ready_install"] += 1
            b["total_sqf"] += o.total_sqf or 0.0
            b["pending_revenue"] += o.total_dealer_charge or 0.0
        dealers = sorted(
            dealer_buckets.values(), key=lambda b: -b["count"]
        )
        for b in dealers:
            b["total_sqf"] = round(b["total_sqf"], 1)
            b["pending_revenue"] = round(b["pending_revenue"], 2)

        # ---------- Pipeline preview ----------
        Stage = self.env["indigo.stage"]
        stages_by_code = {
            s.code: s for s in Stage.search([("code", "in", PIPELINE_PREVIEW_CODES)])
        }
        pipeline = []
        for code in PIPELINE_PREVIEW_CODES:
            stage = stages_by_code.get(code)
            if not stage:
                continue
            cards = Order.search(
                [("stage_id", "=", stage.id)],
                order="last_stage_change asc",
            )
            oldest = cards[:1]
            pipeline.append({
                "code": code,
                "stage_id": stage.id,
                "name": stage.name,
                "count": len(cards),
                "oldest": (oldest and {
                    "id": oldest.id,
                    "name": oldest.name,
                    "client": oldest.client_name,
                    "dealer": oldest.dealer_id.name or "",
                    "days": oldest.days_in_current_stage,
                    "is_overdue": oldest.is_overdue,
                }) or None,
            })

        # ---------- Today's installations ----------
        today_orders = Order.search([
            ("installation_date", "=", today),
            ("stage_id.code", "in", ["install_scheduled", "ready_install"]),
        ])
        by_installer = {}
        for o in today_orders:
            installers = o.installer_ids or self.env["res.partner"]
            if not installers:
                by_installer.setdefault(0, {
                    "installer_id": 0,
                    "installer_name": "Unassigned",
                    "orders": [],
                })
                by_installer[0]["orders"].append({
                    "id": o.id, "name": o.name,
                    "client": o.client_name, "address": o.client_address,
                })
                continue
            for inst in installers:
                bucket = by_installer.setdefault(inst.id, {
                    "installer_id": inst.id,
                    "installer_name": inst.name,
                    "orders": [],
                })
                bucket["orders"].append({
                    "id": o.id, "name": o.name,
                    "client": o.client_name, "address": o.client_address,
                })
        today_installs = sorted(
            by_installer.values(), key=lambda b: b["installer_name"]
        )

        # ---------- Health signals ----------
        overdue_count = Order.search_count(
            [("is_overdue", "=", True), ("stage_id.code", "not in", list(CLOSED_CODES))]
        )
        if active_orders:
            total_days = sum((o.days_in_current_stage or 0) for o in active_orders)
            avg_aging = round(total_days / len(active_orders), 1)
        else:
            avg_aging = 0.0
        week_due = Order.search_count([
            ("expected_completion_date", ">=", week_ago),
            ("expected_completion_date", "<=", today),
        ])
        week_installed = Order.search_count([
            ("stage_id.code", "in", ["installed"] + list(CLOSED_CODES)),
            ("write_date", ">=", fields.Datetime.to_string(
                fields.Datetime.now() - timedelta(days=7)
            )),
        ])

        return {
            "kpis": {
                "active_count": active_count,
                "created_week": created_week,
                "pending_install": pending_install,
                "revenue_month": round(revenue_month, 2),
            },
            "dealers": dealers,
            "pipeline": pipeline,
            "today_installs": today_installs,
            "health": {
                "overdue_count": overdue_count,
                "avg_aging": avg_aging,
                "week_due": week_due,
                "week_installed": week_installed,
            },
            "generated_at": fields.Datetime.now().isoformat(),
        }
