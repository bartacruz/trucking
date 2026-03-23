from odoo import _, api, fields, models
import logging

_logger = logging.getLogger(__name__)

class WhatsappTemplateButton(models.Model):
    _inherit = "mail.whatsapp.template.button"
    
    # action_server_ids = fields.One2many("ir.actions.server", "base_automation_id",
    #     context={'default_usage': 'base_automation'},
    #     string="Actions",
    #     compute="_compute_action_server_ids",
    #     store=True,
    #     readonly=False,
    # )
    def action_pressed(self, author, message):
        self.ensure_one()
        
        confirm_template_id = self.env["ir.config_parameter"].sudo().get_param("trucking.wat_driver_confirm")
        if confirm_template_id  and self.template_id.id == int(confirm_template_id):
            trip = message.trucking_trip_id
            _logger.warning("Button %s pressed for trip %s, author %s, message %s",self.name,trip.name,author.name,message)
            if not trip or author.active_trucking_trip_id != trip:
                return
            if self.name =="Confirm":
                # Okay, this is a driver confiming a trip.
                trip.driver_response = 'confirmed'
                body = 'Confirmación recibida.\nNos estaremos contactando para mas detalles.'
            else:
                trip.driver_response = 'rejected'
                body = 'Cancelación recibida.'
            trip._send_whatsapp(self.author_id,body=body)
                
        return super().action_pressed(author, message)