from odoo import _, api, fields, models
from datetime import timedelta
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    trucking_trip_id = fields.Many2one(
        'trucking.trip', 
        string="Trip",
        ondelete='cascade',
    )

    cloned_line_id = fields.Many2one('sale.order.line')
    distance = fields.Float(string="Distance (km)")
   
    _sql_constraints = [
        ('trucking_trip_unique', 'unique(trucking_trip_id)', '¡Este viaje ya está asignado a otra línea de pedido!')
    ]
    
    def create(self, vals_list):
        records = super().create(vals_list)
        records_with_trips = records.filtered(lambda L: L.product_id.trucking_trip and not L.trucking_trip_id)
        print("records_with_trips",records_with_trips)
        records_with_trips._create_associated_trip()
            
    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)

        if 'product_id' in vals:
            for line in self:
                if not line.product_id.trucking_trip and line.trucking_trip_id:
                    line.trucking_trip_id.unlink()
                elif line.product_id.trucking_trip and not line.trucking_trip_id:
                    line._create_associated_trip()
        return res
    
    def _create_associated_trip(self):
        created_trips = self.env['trucking.trip']
        for record in self:
            vals = record._prepare_trucking_values()
            print("creating trip",record, record.order_id,vals)
            trip = record.trucking_trip_id.create([vals])
            record.order_id._post_trip_message(trip)
    
    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced', 'trucking_trip_id.state')
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        for line in self:
            if line.trucking_trip_id:
                if line.trucking_trip_id.state in ['completed', 'cancelled']:
                    line.invoice_status = 'to invoice'
                else:
                    line.invoice_status = 'no'
                print("_compute_invoice_status",line,line.trucking_trip_id.state,line.invoice_status)
                
    @api.depends('order_id.pricelist_id','product_uom_qty', 'distance')
    def _compute_price_unit(self):
        super()._compute_price_unit()
        print("computed price_unit of ",self,self.mapped('price_unit'))
        
        
    @api.depends('order_id.pricelist_id', 'distance', 'product_uom_qty')
    def _compute_pricelist_item_id(self):
        
        for line in self:
            qty_field=line.order_id.pricelist_id.qty_field or 'product_uom_qty'
            quantity = getattr(line, qty_field ) or 1
            print("checking pricelist_item of",line,"with",qty_field," quantity",quantity)
            line.pricelist_item_id = line.order_id.pricelist_id._get_product_rule(
                line.product_id,
                quantity=quantity,
                date=line._get_order_date(),
            )
            
                
    def _prepare_trucking_values(self, **kwargs):
        """
        Prepare the values to create a new Trucking Trip from a sale order line.
        """
        self.ensure_one()

        return {
            "sale_line_id": self.id,
            "state": 'draft',
            "company_id": self.company_id.id,
            "origin_locality_id": self.order_id.origin_locality_id.id or None,
            "destination_locality_id": self.order_id.destination_locality_id.id or None,
            "commitment_date": self.order_id.commitment_date,
        }
    