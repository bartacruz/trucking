from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime, formatLang


class Pricelist(models.Model):
    _inherit = "product.pricelist"
    
    qty_field = fields.Selection([
            ('product_uom_qty',_('Order Qty')),
            ('distance',_('Distance')),
        ],
        string= _("Qty Field"),
        default="product_uom_qty",
        required=True
    )
    