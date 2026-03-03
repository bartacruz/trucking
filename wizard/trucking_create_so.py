from odoo import _,api, fields, models

class TruckingCreateSO(models.TransientModel):
    _name = "trucking.create.so"
    _description = "Create a transport sale with trips"
    
    company_id = fields.Many2one('res.company',default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    
    order_id = fields.Many2one('sale.order', string="Order")
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    commitment_date = fields.Datetime(string="Fecha de Entrega", default=fields.Datetime.now)
    
    product_id = fields.Many2one('product.product')
    pricelist_id = fields.Many2one('product.pricelist')
    price_unit = fields.Monetary(_("Rate"), 'currency_id' )
    
    origin_locality = fields.Many2one('afip.locality')
    destination_locality = fields.Many2one('afip.locality')
    qty = fields.Integer("Trucks",default=1)
    distance = fields.Integer(_("Estimated Distance"),default=1)
    start = fields.Datetime(string="Scheduled start")
    end = fields.Datetime(string="Scheduled end")
    sale_label = fields.Char(compute="_compute_label")

    order_confirmed = fields.Boolean(readonly=True)

    @api.onchange("origin", "destination", "start", "end")
    def _compute_readonly_fields(self):
        state = self.order_id.state
        if state == "sale" or state == "cancelled":
            self.order_confirmed = True
        else:
            self.order_confirmed = False
            
    def create_sale_order(self):
        qty =1
        order_line = [
            (0, 0, {'product_id': self.product_id.id, 
                    "product_uom_qty": qty,
                    "product_uom": self.product_id.uom_id.id,
                    'distance': self.distance,
                    'price_unit': self.price_unit or self.product_id.list_price
                    }
                ) 
        ]
        vals_list = [{
            "partner_id": self.partner_id.id,
            "commitment_date": self.commitment_date,
            "state": "draft",
            'origin_locality_id':self.origin_locality.id,
            'destination_locality_id':self.destination_locality.id,
            'pricelist_id': self.pricelist_id.id,
            "order_line": order_line*self.qty,
        } ]
        print("vals",vals_list)
        self.env["sale.order"].create(vals_list)

