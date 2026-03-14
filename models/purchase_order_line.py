from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    trucking_trip_id = fields.Many2one('trucking.trip')
    trucking_trip_state = fields.Selection(related='trucking_trip_id.state', store=True)
    
    sale_line_need_update= fields.Boolean(compute="_compute_sale_line_need_update", store=True)
    
    @api.depends('sale_line_id.price_unit','sale_line_id.product_uom_qty','sale_line_id.qty_delivered','partner_id.purchase_general_discount')
    def _compute_sale_line_need_update(self):
        for line in self:
            if line.trucking_trip_id and line.sale_line_id:
                # TODO substract commision (purchase pricelists??)
                line.price_unit = line.sale_line_id.price_unit
                line.product_uom_qty = line.sale_line_id.product_uom_qty
                line.discount = line.partner_id.purchase_general_discount
                line.qty_received = line.sale_line_id.qty_delivered
                print("*********updated purchase line",line,line.sale_line_id)
            line.sale_line_need_update = False