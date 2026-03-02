from odoo import _, api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    trucking_driver = fields.Boolean(_('Trucking driver'))
    