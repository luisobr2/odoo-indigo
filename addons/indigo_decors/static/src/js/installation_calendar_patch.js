/** @odoo-module **/

/**
 * Custom Calendar view for "Installations Calendar".
 *
 * When the user clicks "+ New" or clicks on an empty day in the calendar,
 * the standard Odoo behavior is to open a NEW indigo.order form.
 * That is wrong for this calendar: the goal is to assign an installation
 * date to an order that ALREADY exists.
 *
 * This patch overrides the controller's createRecord() to open the
 * `indigo.installation.schedule.wizard` instead, with the clicked date
 * pre-filled.
 */
import { calendarView } from "@web/views/calendar/calendar_view";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class InstallationCalendarController extends CalendarController {
    setup() {
        super.setup();
        // Re-declare in case the parent's `this.action` is not yet visible
        // when createRecord is called from the renderer's onDateClick.
        this.indigoAction = useService("action");
    }

    createRecord(record) {
        const actionService = this.indigoAction || this.action;
        // record.start is a Luxon DateTime — convert to ISO date.
        let isoDate;
        try {
            isoDate = record.start.toISODate
                ? record.start.toISODate()
                : new Date(record.start).toISOString().slice(0, 10);
        } catch (_e) {
            isoDate = false;
        }
        return actionService.doAction({
            type: "ir.actions.act_window",
            name: "Schedule Installation",
            res_model: "indigo.installation.schedule.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: isoDate ? { default_installation_date: isoDate } : {},
        });
    }
}

export const installationCalendarView = {
    ...calendarView,
    Controller: InstallationCalendarController,
};

registry.category("views").add("indigo_installation_calendar", installationCalendarView);
