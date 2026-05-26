# -*- coding: utf-8 -*-
"""
Placeholders para SMS / WhatsApp.

Para activar SMS y/o WhatsApp en produccion, configurar credenciales en
Settings > General Settings > Indigo o como ir.config_parameter:
    indigo.twilio_account_sid
    indigo.twilio_auth_token
    indigo.twilio_sms_from
    indigo.twilio_whatsapp_from

Cuando los parametros NO estan seteados, los metodos solo loguean al chatter de la orden
("Would send SMS / WhatsApp..."). Esto deja el codigo listo para conectar Twilio
sin tener que tocar nada cuando el cliente provea las credenciales.
"""
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    indigo_notification_channels = fields.Selection(
        [
            ("email", "Solo email"),
            ("email_sms", "Email + SMS"),
            ("email_whatsapp", "Email + WhatsApp"),
            ("all", "Email + SMS + WhatsApp"),
        ],
        string="Canales de notificacion",
        default="email",
        help="Como recibira las notificaciones de cambio de etapa.",
    )


class IndigoOrder(models.Model):
    _inherit = "indigo.order"

    def _twilio_params(self):
        Param = self.env["ir.config_parameter"].sudo()
        return {
            "sid": Param.get_param("indigo.twilio_account_sid", ""),
            "token": Param.get_param("indigo.twilio_auth_token", ""),
            "sms_from": Param.get_param("indigo.twilio_sms_from", ""),
            "wa_from": Param.get_param("indigo.twilio_whatsapp_from", ""),
        }

    def _send_sms(self, recipients, message):
        """recipients: lista de res.partner. Si no hay credenciales Twilio, logea."""
        params = self._twilio_params()
        configured = bool(params["sid"] and params["token"] and params["sms_from"])
        for partner in recipients:
            phone = (partner.mobile or partner.phone or "").strip()
            if not phone:
                _logger.info("Indigo SMS: skip %s (sin telefono)", partner.name)
                continue
            if not configured:
                # Placeholder: solo logea al chatter
                self.message_post(body="[SMS pendiente] Para %s (%s): %s<br/><em>Configura indigo.twilio_* para envio real.</em>" % (
                    partner.name, phone, message
                ))
                _logger.info("Indigo SMS [no Twilio]: %s -> %s | %s", partner.name, phone, message)
                continue
            # Envio real (requiere `pip install twilio` en el contenedor)
            try:
                from twilio.rest import Client
                client = Client(params["sid"], params["token"])
                msg = client.messages.create(
                    body=message,
                    from_=params["sms_from"],
                    to=phone,
                )
                self.message_post(body="[SMS enviado a %s] sid=%s" % (partner.name, msg.sid))
            except Exception as e:
                _logger.exception("Indigo SMS Twilio error: %s", e)
                self.message_post(body="[SMS ERROR para %s]: %s" % (partner.name, e))

    def _send_whatsapp(self, recipients, message):
        params = self._twilio_params()
        configured = bool(params["sid"] and params["token"] and params["wa_from"])
        for partner in recipients:
            phone = (partner.mobile or partner.phone or "").strip()
            if not phone:
                continue
            if not configured:
                self.message_post(body="[WhatsApp pendiente] Para %s (%s): %s<br/><em>Configura indigo.twilio_* para envio real.</em>" % (
                    partner.name, phone, message
                ))
                continue
            try:
                from twilio.rest import Client
                client = Client(params["sid"], params["token"])
                msg = client.messages.create(
                    body=message,
                    from_="whatsapp:" + params["wa_from"],
                    to="whatsapp:" + phone,
                )
                self.message_post(body="[WhatsApp enviado a %s] sid=%s" % (partner.name, msg.sid))
            except Exception as e:
                _logger.exception("Indigo WhatsApp error: %s", e)
                self.message_post(body="[WhatsApp ERROR para %s]: %s" % (partner.name, e))

    def _dispatch_stage_notification(self):
        """Llamado opcionalmente al cambiar etapa para mandar email + SMS + WhatsApp
        segun el canal preferido de cada destinatario."""
        self.ensure_one()
        message = "Indigo: tu orden %s entro a la etapa %s." % (self.name, self.stage_id.name)
        # Email ya lo manda write() via mail.template
        for user in self.assigned_user_ids:
            partner = user.partner_id
            ch = partner.indigo_notification_channels or "email"
            if ch in ("email_sms", "all"):
                self._send_sms([partner], message)
            if ch in ("email_whatsapp", "all"):
                self._send_whatsapp([partner], message)
