from odoo import _, api, fields, models
from markupsafe import Markup

class SaleOrder(models.Model):
    _inherit = "sale.order"

    trucking_trip_ids = fields.One2many('trucking.trip','sale_id')
    has_trucking_trips = fields.Boolean(compute='_compute_tracking_trips',store=True)
    trucking_trip_active = fields.Boolean(compute='_compute_tracking_trips',store=True)
    
    origin_locality_id = fields.Many2one('afip.locality',tracking=True)
    destination_locality_id = fields.Many2one('afip.locality',tracking=True)
    
    @api.depends('order_line.product_id','trucking_trip_ids')
    def _compute_tracking_trips(self):
        for record in self:
            lines_with_trips = record.order_line.filtered(lambda L: L.product_id.trucking_trip)
            record.has_trucking_trips = len(lines_with_trips) > 0
            record.trucking_trip_active = len(lines_with_trips.filtered(lambda L: L.trucking_trip_id.state not in ['completed','cancelled']) ) >0
            print("line_with_trips",lines_with_trips)
            record._trucking_generate()
        
    def _generate_line_trucking_trips(self, new_trucking_sol):
        """
        Generate Trucking Trips for the given sale order lines.
        """
        self.ensure_one()
        new_trucking_trips = self.env["trucking.trip"]

        for line in new_trucking_sol:
            if not line.trucking_trip_id:
                vals = line._prepare_trucking_values()
                print("trip vals",vals)
                trip_by_line = self.env["trucking.trip"].sudo().create(vals)
                print("trip_by_line",trip_by_line)
                # line.trucking_trip_id = trip_by_line
                # line.write({"trucking_trip_id": [(4, trip_by_line.id)]})
                new_trucking_trips |= trip_by_line
                print("new trip",trip_by_line,line.trucking_trip_id)
                

        return new_trucking_trips

    def _trucking_generate(self):
        self.ensure_one()
        new_trucking_trips = self.env["trucking.trip"]

        new_trucking_sol = self.order_line.filtered(
            lambda L: L.product_id.trucking_trip and not L.trucking_trip_id
        )
        print("new lines:", self,[(x,x.order_id,x.trucking_trip_id) for x in new_trucking_sol])
        new_trucking_trips |= self._generate_line_trucking_trips(new_trucking_sol)
        self._post_trip_message(new_trucking_trips)
        
        # TODO: Check for lines with trucking_trip_id and product that is not a trip.
        
        return new_trucking_trips
    
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

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if "order_line" in vals and order.has_trucking_trips:
            order._trucking_generate()
        return order
    
    def action_trucking_clone_tms(self):
        product_id = self.env['product.template'].search([ ('trucking_trip','=',True) ], limit=1)
        kg_uom = self.env.ref('uom.product_uom_kgm')
        created_orders = self.env[self._name]
        for record in self:
            lines = []
            for line in record.order_line.filtered(lambda L: len(L.tms_order_ids) > 0):
                delivered = kg_uom._compute_quantity(line.tms_order_ids[0].delivered_total,product_id.uom_id)
                lines.append(
                    (0, 0, {'product_id': product_id.id, 
                        "product_uom_qty": delivered,
                        "product_uom": product_id.uom_id.id,
                        "qty_delivered": delivered,
                        "cloned_line_id": line.id,
                        }
                    ) 
                )
            vals_list = [{
                "partner_id": self.partner_id.id,
                "partner_invoice_id": self.partner_invoice_id.id,
                "commitment_date": self.commitment_date,
                "state": "sent",
                "pricelist_id": self.pricelist_id.id,
                'origin_locality_id':self.tms_origin_locality_id.id,
                'destination_locality_id':self.tms_destination_locality_id.id,
                "order_line": lines,
            } ]
            print("vals",vals_list)
            order = self.env["sale.order"].create(vals_list)
            
            message = _(
                "Order cloned from: %s", 
                Markup(
                    f"""<a href=# data-oe-model=sale.order data-oe-id={record.id}"""
                    f""">{record.name}</a>"""
                )
            )
            order.message_post(body=message)
            
            created_orders |= order
            
        created_orders.mapped('order_line').mapped('trucking_trip_id')._convert_from_tms()
            
        action = {
            'name': _('Sales Order(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'target': 'current',
        }
        if len(created_orders) == 1:
            action['res_id'] = created_orders[0].id
            action['view_mode'] = 'form'
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', created_orders.ids)]
         
        return action
    
    def action_create_trucking_order(self):
        return False