from odoo import _,api, fields, models

class TruckingCreateSO(models.TransientModel):
    
    _name = "trucking.create.so"
    _description = "Create a transport sale with trips"
    
    def _default_product(self):
        # TODO: get it from settings
        return self.env['product.product'].search([ ('trucking_trip','=',True) ], limit=1)
    
    
    company_id = fields.Many2one('res.company',default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    
    order_id = fields.Many2one('sale.order', string="Order")
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    commitment_date = fields.Datetime(string="Fecha de Entrega", default=fields.Datetime.now)
    
    product_id = fields.Many2one('product.product', default=lambda self: self._default_product())
    pricelist_id = fields.Many2one('product.pricelist')
    fixed_price = fields.Monetary("Rate", 'currency_id' )
    pricelist_discount = fields.Float(string="Pricelist discount")
    
    origin_locality = fields.Many2one('afip.locality')
    destination_locality = fields.Many2one('afip.locality')
    qty = fields.Integer("Trucks",default=1)
    distance = fields.Integer("Estimated Distance",default=1)
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
                    'price_unit': self.fixed_price or self.product_id.list_price
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
            'pricelist_discount': self.pricelist_discount,
            "order_line": order_line*self.qty,
            'trucking_wizard_distance': self.distance, # save for adding new lines
            'trucking_fixed_price': self.fixed_price
        } ]
        print("vals",vals_list)
        self.env["sale.order"].create(vals_list)

