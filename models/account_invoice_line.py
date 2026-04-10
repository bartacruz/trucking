from odoo import api, fields, models, _

class AccountMoveLine(models.Model):
    """Extend invoice/account move lines (Odoo 13+ uses account.move.line)."""
    _inherit = "account.move.line"

    product_category_id = fields.Many2one('product.category', related='product_id.categ_id', string="Product Category", help="Category of the product")

class AccountMoveLineTemplate(models.Model):
    _name='account.move.line.template'
    
    name = fields.Char('Name')
    template_src = fields.Char()
    
    def render(self,record, default=""):
        result = self.env['mail.render.mixin']._render_template(self.template_src,record._name,record.id)
        return result.get(record.id,default)
        