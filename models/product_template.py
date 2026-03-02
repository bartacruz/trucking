from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    trucking_trip = fields.Boolean(
        string="Trucking service",
        store=True,
        readonly=False,
    )
    
    
    
    