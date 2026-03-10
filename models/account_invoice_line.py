from odoo import api, fields, models, _

class AccountMoveLine(models.Model):
    """Extend invoice/account move lines (Odoo 13+ uses account.move.line)."""
    _inherit = "account.move.line"

    product_category_id = fields.Many2one('product.category', related='product_id.categ_id', string="Product Category", help="Category of the product")
