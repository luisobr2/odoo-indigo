# -*- coding: utf-8 -*-
"""Dos etapas de pintura: Michel e Indigo (pedido de Majela, 2026-09-29).

    "agregar dos stage de pintura. Uno seria Michel y el otro Indigo.
     En Indigo hay que poner dos pintores Elio y Mandy. En el stage de Indigo
     que haga un reporte como mismo lo hace ahora, lo unico agregar el nombre
     de quien pinta y que el precio x sqf es 4"

Como queda:

  CNC -> Painting - Michel  (la etapa `painting` de siempre, renombrada)
      -> Painting - Indigo  (etapa nueva `painting_indigo`)
      -> Ready for Installation

* Quien pinta y en que taller se guarda en la regla de pago del pintor
  (`indigo.contractor.rate` con `partner_id` y `paint_shop`): la misma fila de
  Settings dice quien es pintor, donde pinta y cuanto cobra. La lista de
  pintores de la app sale de ahi.
* Al ENTRAR en la etapa de Michel la orden queda con Michel de pintor; al
  entrar en la de Indigo, un pintor que no sea de Indigo se quita, para que
  se elija Elio o Mandy.
* De la etapa de Indigo no se puede AVANZAR sin pintor de Indigo: su pago
  depende de quien la pinto.
* El pago al pintor se genera al avanzar desde cualquiera de las dos etapas,
  con la tarifa de ese pintor (ver indigo_order.py).
"""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .indigo_order import PAINT_DONE_STAGE_CODES

PAINT_SHOPS = [("michel", "Michel"), ("indigo", "Indigo")]
PAINT_STAGE_XMLIDS = ("indigo_decors.stage_painting", "indigo_decors.stage_painting_indigo")
SHOP_OF_STAGE = {"painting": "michel", "painting_indigo": "indigo"}
PAINT_STAGE_CODES = tuple(SHOP_OF_STAGE)

# Reglas de acceso que miraban solo la etapa `painting`. Estan en un XML con
# noupdate, asi que la actualizacion del modulo no las cambia: se reescriben
# aqui (y en el XML, para las instalaciones nuevas). Solo si siguen como las
# dejo el modulo: si alguien las cambio a mano despues, no se pisan.
_RULE_DOMAINS = {
    "indigo_decors.rule_indigo_order_cnc": (
        "[('stage_id.code', 'in', ['cnc', 'painting'])]",
        "[('stage_id.code', 'in', ['cnc', 'painting', 'painting_indigo'])]",
    ),
    "indigo_decors.rule_indigo_order_painter": (
        "[('stage_id.code', '=', 'painting')]",
        "[('stage_id.code', 'in', ['painting', 'painting_indigo'])]",
    ),
    "indigo_decors.rule_indigo_order_line_cnc": (
        "[('order_id.stage_id.code', 'in', ['cnc', 'painting'])]",
        "[('order_id.stage_id.code', 'in', ['cnc', 'painting', 'painting_indigo'])]",
    ),
    "indigo_decors.rule_indigo_order_line_painter": (
        "[('order_id.stage_id.code', '=', 'painting')]",
        "[('order_id.stage_id.code', 'in', ['painting', 'painting_indigo'])]",
    ),
}
_STAGE_NAMES = {
    "indigo_decors.stage_painting": {"en_US": "Painting – Michel", "es_ES": "Pintura – Michel"},
    "indigo_decors.stage_painting_indigo": {"en_US": "Painting – Indigo", "es_ES": "Pintura – Indigo"},
}
# Nombres que la migracion puede reemplazar: los de antes y los que ella
# misma puso en una version anterior (en ingles tambien en es_ES).
_OLD_STAGE_NAMES = {"", "Painting", "Pintura", "Painting – Michel", "Painting – Indigo"}


class IndigoContractorRate(models.Model):
    _inherit = "indigo.contractor.rate"

    paint_shop = fields.Selection(
        PAINT_SHOPS,
        string="Paint shop",
        help="Only for a painter's own rule: which painting stage this person "
             "paints in. Painters with a shop are the ones offered when an "
             "order is assigned.",
    )


class IndigoStage(models.Model):
    _inherit = "indigo.stage"

    @api.model
    def _indigo_setup_paint_stages(self):
        """Idempotente, corre en cada actualizacion del modulo."""
        langs = set(self.env["res.lang"].sudo().search([]).mapped("code"))
        for xmlid, names in _STAGE_NAMES.items():
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if not stage:
                continue
            for lang, name in names.items():
                if lang not in langs:
                    continue
                current = (stage.with_context(lang=lang).name or "").strip()
                if current != name and current in _OLD_STAGE_NAMES:
                    stage.with_context(lang=lang).write({"name": name})
        for xmlid, (old, new) in _RULE_DOMAINS.items():
            rule = self.env.ref(xmlid, raise_if_not_found=False)
            if rule and (rule.domain_force or "").strip() == old:
                rule.sudo().write({"domain_force": new})
        return True


class IndigoOrderPaintShops(models.Model):
    _inherit = "indigo.order"

    paint_shop = fields.Selection(
        PAINT_SHOPS,
        string="Paint shop",
        compute="_compute_paint_shop",
        help="Which painting stage the order is in (Michel or Indigo), if any.",
    )

    @api.depends("stage_id.code")
    def _compute_paint_shop(self):
        for order in self:
            order.paint_shop = SHOP_OF_STAGE.get(order.stage_id.code or "", False)

    @api.model
    def _indigo_paint_stages(self):
        stages = self.env["indigo.stage"]
        for xmlid in PAINT_STAGE_XMLIDS:
            stages |= self.env.ref(xmlid, raise_if_not_found=False) or self.env["indigo.stage"]
        return stages

    def _indigo_painter_rules(self, shop=None):
        domain = [
            ("contractor_type", "=", "painter"),
            ("partner_id", "!=", False),
            ("paint_shop", "!=", False),
        ]
        if shop:
            domain.append(("paint_shop", "=", shop))
        return self.env["indigo.contractor.rate"].sudo().search(domain)

    @api.model
    def _indigo_painters(self, shop=None):
        """Los pintores: quien tiene su propia regla de pago de pintor con
        taller. Con `shop`, solo los de ese taller."""
        return self._indigo_painter_rules(shop).mapped("partner_id")

    @api.model
    def _indigo_painter_shop(self, partner):
        if not partner:
            return False
        rule = self.env["indigo.contractor.rate"].sudo().search([
            ("contractor_type", "=", "painter"),
            ("partner_id", "=", partner.id),
            ("paint_shop", "!=", False),
        ], limit=1)
        return rule.paint_shop or False

    @api.model
    def indigo_painters_list(self):
        """Para la app: los pintores con su taller y tarifa. Solo usuarios
        internos: el portal (dealers) no ve cuanto cobra nadie."""
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only the team can see the painters."))
        return [
            {"id": r.partner_id.id, "name": r.partner_id.name, "shop": r.paint_shop, "rate": r.rate}
            for r in self._indigo_painter_rules()
        ]

    def _indigo_has_painter_payout(self):
        self.ensure_one()
        return bool(self.env["indigo.payout.line"].sudo().search_count([
            ("order_id", "=", self.id),
            ("payout_id.contractor_type", "=", "painter"),
            ("payout_id.state", "!=", "cancel"),
        ]))

    def _indigo_expected_paint_rate(self):
        """La tarifa por SQF con la que se le va a pagar la pintura de esta
        orden, o None si todavia no se sabe (Indigo sin pintor elegido y con
        pintores de tarifas distintas)."""
        self.ensure_one()
        if self.painter_id:
            return self._get_painter_rate(self.painter_id)
        shop = SHOP_OF_STAGE.get(self.stage_id.code or "")
        if shop:
            rates = set(self._indigo_painter_rules(shop).mapped("rate"))
            if len(rates) == 1:
                return rates.pop()
            if shop == "indigo":
                return None
        return self._get_painter_rate()

    def _indigo_painter_sheet_info(self):
        """Lo que la hoja del pintor necesita: la tarifa de cada orden (la de
        su pintor, la de su taller o la general; None si no se sabe), si
        mostrar la columna del pintor y el taller, cuando todas son del mismo."""
        rates = {o.id: o._indigo_expected_paint_rate() for o in self}
        known = {r for r in rates.values() if r is not None}
        shops = {SHOP_OF_STAGE.get(o.stage_id.code or "") for o in self}
        shop = shops.pop() if len(shops) == 1 else False
        return {
            "rates": rates,
            "single_rate": known.pop() if len(known) == 1 and None not in rates.values() else False,
            "show_painter": bool(self.mapped("painter_id")) or shop == "indigo",
            "shop_label": dict(PAINT_SHOPS).get(shop, "") if shop else "",
        }

    def _indigo_painter_mismatch(self, order, painter):
        """Mensaje si `painter` no pinta en la etapa de pintura de `order`
        (cuando ese taller ya tiene pintores configurados), o None."""
        shop = SHOP_OF_STAGE.get(order.stage_id.code or "")
        if not shop or not painter:
            return None
        shop_painters = self._indigo_painters(shop)
        if not shop_painters or self._indigo_painter_shop(painter) == shop:
            return None
        return _(
            "%(painter)s doesn't paint at %(shop)s. Painters there: %(names)s."
        ) % {
            "painter": painter.name,
            "shop": dict(PAINT_SHOPS)[shop],
            "names": ", ".join(shop_painters.mapped("name")),
        }

    def write(self, vals):
        moving = "stage_id" in vals
        if moving:
            self._indigo_before_paint_move(vals)
        elif vals.get("painter_id"):
            painter = self.env["res.partner"].browse(vals["painter_id"])
            for order in self:
                msg = self._indigo_painter_mismatch(order, painter)
                if msg:
                    raise UserError(msg)
        res = super().write(vals)
        if moving:
            self._indigo_painter_for_stage(explicit="painter_id" in vals)
        return res

    def _indigo_before_paint_move(self, vals):
        """Antes de que una puerta salga de pintura hacia instalacion:
        en Indigo tiene que estar dicho quien la pinto (su pago depende de
        eso); en la de Michel, si no tiene pintor (una puerta que ya estaba
        ahi antes de las dos etapas), la pinto Michel."""
        target = self.env["indigo.stage"].browse(vals["stage_id"]) if vals.get("stage_id") else None
        if not target or target.code not in PAINT_DONE_STAGE_CODES:
            return
        explicit = "painter_id" in vals
        new_painter = self.env["res.partner"].browse(vals["painter_id"]) if vals.get("painter_id") else self.env["res.partner"]
        for order in self:
            shop = SHOP_OF_STAGE.get(order.stage_id.code or "")
            if not shop or order.cancelled_at:
                continue
            painter = new_painter if explicit else order.painter_id
            if shop == "indigo":
                if not painter or self._indigo_painter_shop(painter) != "indigo":
                    names = ", ".join(self._indigo_painters("indigo").mapped("name")) or _("an Indigo painter")
                    raise UserError(_(
                        "%(order)s is in Painting – Indigo: choose who painted it (%(names)s) "
                        "before moving it on. Their pay depends on it."
                    ) % {"order": order.name, "names": names})
            elif not painter and not explicit:
                michel = self._indigo_painters("michel")
                if len(michel) == 1:
                    order.sudo().painter_id = michel.id
                    order.sudo()._message_log(body=_(
                        "Painter set to %s: the door was painted in Painting – Michel."
                    ) % michel.name)

    def _indigo_painter_for_stage(self, explicit=False):
        """Al entrar en una etapa de pintura, el pintor tiene que ser de ese
        taller: en la de Michel queda Michel; en la de Indigo se quita el que
        no sea de Indigo, para que se elija Elio o Mandy. Un pintor elegido en
        la misma escritura se respeta (y se valida), y si la puerta ya tiene
        un pago de pintor no se toca: ya se le pago a alguien."""
        for order in self:
            shop = SHOP_OF_STAGE.get(order.stage_id.code or "")
            if not shop:
                continue
            if explicit:
                msg = self._indigo_painter_mismatch(order, order.painter_id)
                if msg:
                    raise UserError(msg)
                continue
            if order._indigo_has_painter_payout():
                continue
            current = self._indigo_painter_shop(order.painter_id)
            if shop == "michel" and current != "michel":
                michel = self._indigo_painters("michel")
                if len(michel) == 1:
                    order.sudo().painter_id = michel.id
            elif shop == "indigo" and order.painter_id and current != "indigo":
                order.sudo().painter_id = False
