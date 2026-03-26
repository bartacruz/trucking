from odoo import _,api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    trip_verified_to_invoice = fields.Boolean(_("Verified to invoice",help="Trips must be verified to be invoiced"),config_parameter="trucking.trip_verified_to_invoice")
    whatsapp_template_driver_confirm_id = fields.Many2one('mail.whatsapp.template', config_parameter="trucking.wat_driver_confirm")
    whatsapp_template_driver_remember_cpe = fields.Many2one('mail.whatsapp.template', config_parameter="trucking.wat_driver_remember_cpe")
    whatsapp_template_customer_notify = fields.Many2one('mail.whatsapp.template', config_parameter="trucking.wat_customer_notify")
    
    
    
class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model
    def set_param(self, key, value):
        res = super(IrConfigParameter, self).set_param(key, value)
        if key == 'trucking.trip_verified_to_invoice':
            lines_to_recompute = self.env['sale.order.line'].search([
                ('state', '=', 'sale'),
                ('invoice_status', '!=', 'invoiced')
            ])
            print("set_param trip_verified_to_invoice",lines_to_recompute)
            if lines_to_recompute:
                # Forzamos el recálculo
                lines_to_recompute._compute_invoice_status()
