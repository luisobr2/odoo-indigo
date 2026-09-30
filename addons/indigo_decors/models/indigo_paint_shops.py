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
from odoo.exceptions import UserError

PAINT_SHOPS = [("michel", "Michel"), ("indigo", "Indigo")]
PAINT_STAGE_XMLIDS = ("indigo_decors.stage_painting", "indigo_decors.stage_painting_indigo")
SHOP_OF_STAGE = {"painting": "michel", "painting_indigo": "indigo"}
PAINT_STAGE_CODES = tuple(SHOP_OF_STAGE)

# Reglas de acceso que miraban solo la etapa `painting`. Estan en un XML con
# noupdate, asi que la actualizacion del modulo no las cambia: se reescriben
# aqui (y en el XML, para las instalaciones nuevas).
_RULE_DOMAINS = {
    "indigo_decors.rule_indigo_order_cnc": "[('stage_id.code', 'in', ['cnc', 'painting', 'painting_indigo'])]",
    "indigo_decors.rule_indigo_order_painter": "[('stage_id.code', 'in', ['painting', 'painting_indigo'])]",
    "indigo_decors.rule_indigo_order_line_cnc": "[('order_id.stage_id.code', 'in', ['cnc', 'painting', 'painting_indigo'])]",
    "indigo_decors.rule_indigo_order_line_painter": "[('order_id.stage_id.code', 'in', ['painting', 'painting_indigo'])]",
}


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
        michel = self.env.ref("indigo_decors.stage_painting", raise_if_not_found=False)
        if michel:
            for lang in ("en_US", "es_ES"):
                current = michel.with_context(lang=lang).name or ""
                if current.strip() in ("Painting", "Pintura", ""):
                    michel.with_context(lang=lang).write({"name": "Painting – Michel"})
        indigo = self.env.ref("indigo_decors.stage_painting_indigo", raise_if_not_found=False)
        if indigo:
            for lang in ("en_US", "es_ES"):
                if not (indigo.with_context(lang=lang).name or "").strip():
                    indigo.with_context(lang=lang).write({"name": "Painting – Indigo"})
        for xmlid, domain in _RULE_DOMAINS.items():
            rule = self.env.ref(xmlid, raise_if_not_found=False)
            if rule and rule.domain_force != domain:
                rule.sudo().write({"domain_force": domain})
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

    @api.model
    def _indigo_painters(self, shop=None):
        """Los pintores: quien tiene su propia regla de pago de pintor con
        taller. Con `shop`, solo los de ese taller."""
        domain = [
            ("contractor_type", "=", "painter"),
            ("partner_id", "!=", False),
            ("paint_shop", "!=", False),
        ]
        if shop:
            domain.append(("paint_shop", "=", shop))
        return self.env["indigo.contractor.rate"].sudo().search(domain).mapped("partner_id")

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
        """Para la app: los pintores con su taller."""
        rules = self.env["indigo.contractor.rate"].sudo().search([
            ("contractor_type", "=", "painter"),
            ("partner_id", "!=", False),
            ("paint_shop", "!=", False),
        ])
        return [
            {"id": r.partner_id.id, "name": r.partner_id.name, "shop": r.paint_shop, "rate": r.rate}
            for r in rules
        ]

    def _indigo_painter_sheet_info(self):
        """Lo que la hoja del pintor necesita: la tarifa de cada orden (la de
        su pintor, o la general), si mostrar la columna del pintor y el
        taller, cuando todas las ordenes son del mismo."""
        rates = {
            o.id: (self._get_painter_rate(o.painter_id) if o.painter_id else self._get_painter_rate())
            for o in self
        }
        values = set(rates.values())
        shops = {SHOP_OF_STAGE.get(o.stage_id.code or "") for o in self}
        shop = shops.pop() if len(shops) == 1 else False
        return {
            "rates": rates,
            "single_rate": values.pop() if len(values) == 1 else False,
            "show_painter": bool(self.mapped("painter_id")),
            "shop_label": dict(PAINT_SHOPS).get(shop, "") if shop else "",
        }

    def write(self, vals):
        if "stage_id" in vals:
            self._indigo_check_paint_exit(vals)
        res = super().write(vals)
        if "stage_id" in vals:
            self._indigo_painter_for_stage()
        return res

    def _indigo_check_paint_exit(self, vals):
        """Una puerta de Indigo no avanza sin saber quien la pinto."""
        indigo = self.env.ref("indigo_decors.stage_painting_indigo", raise_if_not_found=False)
        target = self.env["indigo.stage"].browse(vals["stage_id"]) if vals.get("stage_id") else None
        if not indigo or not target or target.sequence <= indigo.sequence:
            return
        new_painter = self.env["res.partner"].browse(vals["painter_id"]) if vals.get("painter_id") else None
        for order in self:
            if order.stage_id != indigo:
                continue
            painter = new_painter or order.painter_id
            if not painter or self._indigo_painter_shop(painter) != "indigo":
                names = ", ".join(self._indigo_painters("indigo").mapped("name")) or _("an Indigo painter")
                raise UserError(_(
                    "%(order)s is in Painting – Indigo: choose who painted it (%(names)s) "
                    "before moving it on. Their pay depends on it."
                ) % {"order": order.name, "names": names})

    def _indigo_painter_for_stage(self):
        """Al entrar en una etapa de pintura, el pintor tiene que ser de ese
        taller: en la de Michel queda Michel; en la de Indigo se quita el que
        no sea de Indigo, para que se elija Elio o Mandy."""
        for order in self:
            shop = SHOP_OF_STAGE.get(order.stage_id.code or "")
            if not shop:
                continue
            current = self._indigo_painter_shop(order.painter_id)
            if shop == "michel" and current != "michel":
                michel = self._indigo_painters("michel")
                if len(michel) == 1:
                    order.painter_id = michel.id
            elif shop == "indigo" and order.painter_id and current != "indigo":
                order.painter_id = False
