# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class IndigoPayout(models.Model):
    _name = "indigo.payout"
    _description = "Liquidacion a contratista (pintor / instalador)"
    _order = "date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("indigo.payout") or "/",
        tracking=True,
    )
    contractor_id = fields.Many2one(
        "res.partner",
        string="Contratista",
        required=True,
        tracking=True,
        index=True,
    )
    contractor_type = fields.Selection(
        [
            ("painter", "Pintor"),
            ("installer", "Instalador"),
            ("other", "Otro"),
        ],
        string="Tipo",
        required=True,
        tracking=True,
    )
    date = fields.Date(
        string="Fecha emision",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    period_start = fields.Date(string="Periodo desde")
    period_end = fields.Date(string="Periodo hasta")
    work_date = fields.Date(
        string="Dia trabajado",
        index=True,
        help="Jornada que cubre esta liquidacion. El pago al instalador se "
             "calcula por dia (minimo diario, bono por viaje), no por orden, "
             "asi que hay una liquidacion abierta por instalador y por dia. "
             "Vacio en las liquidaciones de pintor, que siguen siendo por SQF.",
    )

    line_ids = fields.One2many("indigo.payout.line", "payout_id", string="Lineas")

    amount = fields.Float(
        string="Monto total (USD)",
        compute="_compute_amount",
        store=True,
        digits=(12, 2),
        tracking=True,
        group_operator="sum",
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("approved", "Aprobada"),
            ("paid", "Pagada"),
            ("cancel", "Cancelada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    notes = fields.Text(string="Notas")

    @api.depends("line_ids.amount")
    def _compute_amount(self):
        for p in self:
            p.amount = sum(p.line_ids.mapped("amount"))

    def action_approve(self):
        self.write({"state": "approved"})

    def action_mark_paid(self):
        self.write({"state": "paid"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    # ------------------------------------------------------------------
    # Regla del dia
    # ------------------------------------------------------------------
    def _apply_day_rule(self):
        """Recalcula los ajustes de la jornada sobre los renglones de trabajo.

        El total del dia no es la suma de las ordenes: es
        `max(minimo, tarifa * puertas) + bono * instalaciones`. Se
        materializa como RENGLONES en vez de pisar `amount` a proposito --
        `amount` sigue siendo la suma de sus lineas, y Majela puede
        explicarle el total al instalador senalando de donde sale cada
        parte en lugar de defender un numero que el sistema calculo solo.

        Solo toca borradores: reescribir plata ya aprobada o entregada
        seria inaceptable.
        """
        Line = self.env["indigo.payout.line"].sudo()
        for payout in self:
            if payout.state != "draft" or payout.contractor_type != "installer":
                continue
            # SIN DIA NO HAY JORNADA. Este guard no es defensivo por gusto:
            # el wizard de liquidacion junta las jornadas de una semana en
            # una sola liquidacion CON periodo y SIN work_date. Aplicarle la
            # regla del dia a eso borraria todos los ajustes al minimo de la
            # semana y calcularia un unico minimo para los siete dias --
            # en la practica, quedarse con la plata de seis jornadas.
            # Tambien cubre a las liquidaciones viejas que la migracion no
            # pudo fechar: sin saber el dia, no hay regla que aplicar.
            if not payout.work_date:
                continue
            work = payout.line_ids.filtered(lambda l: l.line_kind == "work")
            # Sin trabajo no hay jornada: no se paga un minimo por un dia
            # en blanco. Se limpian los ajustes que hubieran quedado.
            payout.line_ids.filtered(lambda l: l.line_kind != "work").unlink()
            if not work:
                continue

            doors = sum(work.mapped("quantity"))
            # `mapped` deduplica, que es lo que se quiere (dos renglones de
            # la misma orden son UNA instalacion). Pero un renglon que
            # perdio su orden desapareceria de la cuenta y el bono de viaje
            # saldria de menos, asi que se cuenta aparte.
            con_orden = work.mapped("order_id")
            huerfanos = work.filtered(lambda l: not l.order_id)
            installs = len(con_orden) + len(huerfanos)
            por_unidad = sum(work.mapped("amount"))
            rule = self.env["indigo.contractor.rate"].resolve_for(
                "installer", payout.contractor_id
            )
            if not rule:
                continue

            # Se le pasa lo que suman los renglones, no las puertas: el
            # total de la jornada tiene que cuadrar con lo que esta escrito
            # en ella, aunque la tarifa haya cambiado despues.
            objetivo = rule.day_amount(
                unit_total=por_unidad, installs=installs, doors=doors
            )
            base = max(rule.daily_minimum or 0.0, por_unidad)
            faltante = base - por_unidad
            if faltante > 0.005:
                Line.create({
                    "payout_id": payout.id,
                    "line_kind": "minimum",
                    "date_work": payout.work_date,
                    # Cuando no se cobra por puerta, el "ajuste" ES la
                    # tarifa diaria; llamarlo ajuste confundiria.
                    "description": (
                        _("Tarifa diaria") if por_unidad <= 0.005
                        else _("Ajuste a minimo diario (%(min).2f)") % {
                            "min": rule.daily_minimum,
                        }
                    ),
                    "quantity": 1.0,
                    "rate": faltante,
                })

            bono = objetivo - base
            if bono > 0.005:
                por_puerta = rule.bonus_unit == "door"
                Line.create({
                    "payout_id": payout.id,
                    "line_kind": "bonus",
                    "date_work": payout.work_date,
                    "description": _("Bono por %(unidad)s (gasolina y peajes)") % {
                        "unidad": _("puerta") if por_puerta else _("instalacion"),
                    },
                    "quantity": doors if por_puerta else installs,
                    "rate": rule.bonus_amount,
                })

    @api.model
    def indigo_recompute_installer_days(self, date_from=None, date_to=None):
        """Consolida y recalcula las jornadas EN BORRADOR de un periodo.

        Deliberadamente manual: reescribir liquidaciones en masa no puede
        pasar como efecto secundario de un deploy.

        Consolida porque el codigo viejo emitia una liquidacion POR ORDEN.
        Un dia con tres ordenes quedo como tres borradores, y si se les
        aplicara la regla por separado cada uno cobraria su propio minimo
        -- tres jornadas por un dia de trabajo. Se juntan los renglones en
        el borrador mas viejo del dia y los que quedan vacios se cancelan
        (nunca se borran: son registros de plata, y quien mire el historico
        tiene que poder ver que existieron y por que se cerraron).

        Nunca toca aprobadas ni pagadas. Devuelve un resumen.
        """
        domain = [("contractor_type", "=", "installer"), ("state", "=", "draft")]
        if date_from:
            domain.append(("work_date", ">=", date_from))
        if date_to:
            domain.append(("work_date", "<=", date_to))
        payouts = self.search(domain, order="id asc")

        por_jornada = {}
        omitidas = self.browse()
        for p in payouts:
            if not p.work_date:
                # Una liquidacion sin dia no es una jornada: o es una
                # consolidacion de periodo (que ya trae los ajustes de cada
                # dia dentro) o una vieja que no se pudo fechar. En los dos
                # casos hay que dejarla en paz -- recalcularla como si fuera
                # un dia le borraria los ajustes de todos los demas.
                omitidas |= p
                continue
            por_jornada.setdefault((p.contractor_id.id, p.work_date), self.browse())
            por_jornada[(p.contractor_id.id, p.work_date)] |= p

        fusionadas = 0
        for grupo in por_jornada.values():
            principal = grupo[0]
            resto = grupo - principal
            if resto:
                resto.mapped("line_ids").sudo().write({"payout_id": principal.id})
                resto.write({
                    "state": "cancel",
                    "notes": "Consolidada en %s: el pago al instalador es por "
                             "jornada, no por orden." % principal.name,
                })
                fusionadas += len(resto)
            principal._apply_day_rule()

        if omitidas:
            _logger.info(
                "indigo_decors: %s liquidaciones sin dia quedaron fuera del "
                "recalculo (consolidaciones de periodo o registros viejos "
                "sin fecha): %s",
                len(omitidas), ", ".join(omitidas.mapped("name")),
            )
        return {
            "jornadas": len(por_jornada),
            "consolidadas": fusionadas,
            "omitidas": len(omitidas),
            "total": sum(
                payout.amount
                for grupo in por_jornada.values()
                for payout in grupo
                if payout.state == "draft"
            ),
        }


class IndigoPayoutLine(models.Model):
    _name = "indigo.payout.line"
    _description = "Linea de liquidacion"
    _order = "date_work desc, id desc"

    payout_id = fields.Many2one(
        "indigo.payout", required=True, ondelete="cascade", index=True
    )
    order_id = fields.Many2one("indigo.order", string="Orden", index=True)
    order_line_id = fields.Many2one("indigo.order.line", string="Pieza")
    date_work = fields.Date(string="Fecha del trabajo", default=fields.Date.context_today)
    description = fields.Char(string="Descripcion", required=True)
    line_kind = fields.Selection(
        [
            ("work", "Trabajo"),
            ("minimum", "Minimo diario"),
            ("bonus", "Bono"),
        ],
        string="Tipo de renglon",
        default="work",
        required=True,
        help="Los renglones de trabajo salen de las ordenes instaladas; los "
             "otros dos los recalcula la regla del dia y se rehacen solos, "
             "asi que no conviene editarlos a mano.",
    )

    quantity = fields.Float(
        string="Cantidad",
        digits=(10, 2),
        help="SQF para pintor, puertas para instalador.",
    )
    rate = fields.Float(string="Tarifa (USD)", digits=(10, 2))
    amount = fields.Float(
        string="Monto (USD)",
        compute="_compute_amount",
        store=True,
        digits=(12, 2),
    )

    @api.depends("quantity", "rate")
    def _compute_amount(self):
        for line in self:
            line.amount = (line.quantity or 0.0) * (line.rate or 0.0)
