from odoo import _, api, fields, models
from markupsafe import Markup

class SaleOrder(models.Model):
    _inherit = "sale.order"

    trucking_trip_ids = fields.One2many('trucking.trip','sale_id')
    has_trucking_trips = fields.Boolean(compute='_compute_trucking_trips',store=True)    
    trucking_trip_active = fields.Boolean(compute='_compute_trucking_trips',store=True)
    trucking_trips_count = fields.Integer(compute='_compute_trucking_trips')
    trucking_trips_to_assign = fields.Integer(compute='_compute_trucking_trips', store=True)
    
    origin_locality_id = fields.Many2one('afip.locality',tracking=True)
    destination_locality_id = fields.Many2one('afip.locality',tracking=True)
    trucking_wizard_distance = fields.Integer()
    
    pricelist_discount = fields.Float(string="Pricelist discount")
    
    cloned_tms_order_ids = fields.Many2many(
        "tms.order",
        compute="_compute_cloned_tms_order_ids",
        string="Transport orders associated to this sale",
        copy=False,
    )
    
    def _compute_cloned_tms_order_ids(self):
        for sale in self:
            print("cCtmo",sale)
            tms = self.env["tms.order"].search(
                [
                    "|",
                    ("cloned_sale_id", "=", sale.id),
                    ("cloned_sale_line_id", "in", sale.order_line.ids),
                ]
            )
            sale.cloned_tms_order_ids = tms
    
    @api.depends('order_line.product_id','trucking_trip_ids','trucking_trip_ids.state')
    def _compute_trucking_trips(self):
        for record in self:
            lines_with_trips = record.order_line.filtered(lambda L: L.product_id.trucking_trip)
            to_assign = lines_with_trips.filtered(lambda t: t.trucking_trip_state == 'draft')
            record.trucking_trips_count = len(lines_with_trips)
            record.trucking_trips_to_assign = len(to_assign)
            record.has_trucking_trips = len(lines_with_trips) > 0
            record.trucking_trip_active = len(lines_with_trips.filtered(lambda L: L.trucking_trip_id.state not in ['completed','cancelled']) ) >0
            print("line_with_trips",lines_with_trips)
                    
    @api.depends('order_line.invoice_status', 'order_line.trucking_trip_id.state')
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        for order in self:
            trips_pending = order.order_line.filtered(lambda l: l.invoice_status =='no' )
            print("invoice_status",order.name,trips_pending)
            if trips_pending:
                order.invoice_status='no'
    
    def _post_trip_message(self, new_trucking_trips):
        """
        Post messages to the Sale Order and the newly created Trucking Trips
        """
        self.ensure_one()
        links = []
        for trip in new_trucking_trips:
            message = _(
                "Trucking Order Created: %s", 
                Markup(
                    f"""<a href=# data-oe-model=trucking.trip data-oe-id={trip.id}"""
                    f""">{trip.name}</a>"""
                ),
            )
            self.message_post(body=message)

    def action_new_trip_sale(self):
        product_id = self.order_line.mapped('product_id').filtered(lambda P: P.trucking_trip)
        if not product_id:
            raise UserWarning(_('This order does not have a trip product'))
        product_id = product_id[0]
        
        qty = product_id.uom_id.category_id == self.env.ref('uom.product_uom_categ_unit') and 1 or 0
        vals = {
            'order_id': self.id,
            'product_id': product_id.id,
            "product_uom_qty": qty,
            "product_uom": product_id.uom_id.id,
            'distance': self.trucking_wizard_distance,
        }
        self.order_line.create([vals])
        return True
    
    def action_to_draft(self):
        self.state = 'draft'
        return True
        
    def action_trucking_clone_tms(self):
        product_id = self.env['product.product'].search([ ('trucking_trip','=',True) ], limit=1)
        print("product found:",product_id)
        if not product_id:
            raise UserWarning('Could not find any trucking trip product')
        for record in self:
            # Prepare for cloning
            record = record.with_context(trucking_clone=True)
            orig_state = record.state
            record.state = 'draft'
            record.origin_locality_id = record.origin_locality_id or record.tms_origin_locality_id 
            record.destination_locality_id = record.destination_locality_id or record.tms_destination_locality_id
            # if not record.origin_locality_id and record.tms_order_ids:
            #     record.origin_locality_id = record.tms_order_ids.origin_locality_id
            # if not record.destination_locality_id and record.tms_order_ids:
            #     record.destination_locality_id = record.tms_order_ids.destination_locality_id
                
            # TODO: Search localities from origin_id and destination_id
            
            kg_uom = record.env.ref('uom.product_uom_kgm')
            created_orders = record.env[record._name]
            for record in record:
                lines = []
                tms_lines = record.order_line.filtered(lambda L: len(L.tms_order_ids) > 0).sorted('id')
                for line in tms_lines:
                    print("changing line",line,"from",line.product_id.name,'to',product_id.name)
                    line.product_id = product_id
            record.state=orig_state
                
    def action_view_trucking_trips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trips',
            'view_mode': 'tree,form',
            'res_model': 'trucking.trip',
            'domain': [('sale_id', '=', self.id)],
            'context': {
                'default_sale_id': self.id,
                'default_order': 'is_active desc, id desc'
            },
        }
        
