/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Indigo Dashboard — single-panel client action that pulls all KPIs in
 * one ORM call (indigo.order.get_dashboard_data) and renders 5 panels:
 *
 *   1. Top KPI cards (4)
 *   2. Orders by Dealer (auto-grows with real dealers)
 *   3. Pipeline preview (6 stage columns, oldest card per column)
 *   4. Today's installations grouped by installer
 *   5. Health signals (overdue, avg aging, week stats)
 *
 * Click handlers navigate to the standard Kanban with domain pre-filtered.
 */
export class IndigoDashboard extends Component {
    static template = "indigo_decors.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, data: null, error: null });

        onWillStart(async () => {
            try {
                this.state.data = await this.orm.call(
                    "indigo.order", "get_dashboard_data", []
                );
            } catch (err) {
                this.state.error = err.message || String(err);
            } finally {
                this.state.loading = false;
            }
        });
    }

    // ---------- formatting helpers ----------
    fmtMoney(n) {
        const v = Number(n || 0);
        return "$" + v.toLocaleString("en-US", {
            minimumFractionDigits: 2, maximumFractionDigits: 2,
        });
    }
    fmtNum(n) {
        return Number(n || 0).toLocaleString("en-US");
    }

    // ---------- navigation: open Kanban filtered ----------
    openKanban(domain, name) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: name || "Orders",
            res_model: "indigo.order",
            view_mode: "kanban,tree,form",
            views: [[false, "kanban"], [false, "tree"], [false, "form"]],
            domain: domain || [],
        });
    }

    onOpenStage(code) {
        return this.openKanban(
            [["stage_id.code", "=", code]],
            `Orders — ${code}`
        );
    }

    onOpenDealer(dealerId, dealerName) {
        return this.openKanban(
            [
                ["dealer_id", "=", dealerId],
                ["stage_id.code", "not in", ["closed", "invoiced"]],
            ],
            `Orders — ${dealerName}`
        );
    }

    onOpenOrder(orderId) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "indigo.order",
            res_id: orderId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    onOpenOverdue() {
        return this.openKanban(
            [["is_overdue", "=", true], ["stage_id.code", "!=", "closed"]],
            "Overdue orders"
        );
    }

    onOpenAll() {
        return this.openKanban(
            [["stage_id.code", "not in", ["closed", "invoiced"]]],
            "All active orders"
        );
    }

    onNewOrder() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "indigo.order",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    onOpenCalendar() {
        return this.action.doAction("indigo_decors.action_indigo_order_calendar");
    }
}

registry.category("actions").add("indigo_dashboard", IndigoDashboard);
