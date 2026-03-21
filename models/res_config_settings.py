from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    #default_product_id = fields.Many2one('product.template')
    whatsapp_template_driver_confirm_id = fields.Many2one('mail.whatsapp.template')
    whatsapp_template_driver_remember_cpe = fields.Many2one('mail.whatsapp.template')
    whatsapp_template_customer_notify = fields.Many2one('mail.whatsapp.template')
    