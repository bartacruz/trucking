from datetime import datetime, timedelta

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from markupsafe import Markup

import logging

_logger = logging.getLogger(__name__)

class TruckingTrip(models.Model):
    _name = 'trucking.trip'
    _description = 'Trucking Trip'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'
    
    def _default_product(self):
        # TODO: get it from settings
        return self.env['product.product'].search([ ('trucking_trip','=',True) ], limit=1)
    
    state = fields.Selection([
        ('draft','Draft'), # dark 
        ('assigned','Assigned'), # secondary fa-user
        ('confirmed','Confirmed'), #primary fa-user
        ('started','Started'),     # primary fa-truck
        ('arrived','Arrived'),     # primary fa-home 
        ('completed','Completed'), # success fa-check-circle
        ('cancelled','Cancelled',) # danger fa-ban
        
        ],
        compute='_compute_state',
        readonly=True,
        store=True,
        tracking=True
    )
    
    is_active = fields.Boolean(compute='_compute_is_active', store=True)
    cancelled = fields.Boolean()
    
    name = fields.Char(
        required=True,
        copy=False,
        readonly=False,
        index="trigram",
        default=lambda self: _("New"),
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Company related to this order",
    )
    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one("res.partner", _("Partner"), related="sale_id.partner_id", store=True, tracking=True)
    customer_id = fields.Many2one("res.partner", _("Customer"), related="sale_id.partner_shipping_id", store=True, tracking=True)
    
    driver_id = fields.Many2one(
        'res.partner', string=_("Driver"),
        tracking=True, domain=[('truck_driver','=',True)]
    )
    
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string="Truck",
        compute="_compute_vehicle_id", store=True, readonly=False,
        domain=[('vehicle_type', '=', 'truck')], tracking=True
    )

    trailer_id = fields.Many2one(
        related='vehicle_id.trailer_id', string="Trailer",
        store=True, readonly=False
    )

    contact_phone = fields.Char(compute = '_compute_contact_phone')
    driver_phone =  fields.Char(compute='_compute_driver_phone')
    
    
    origin_locality_id = fields.Many2one('afip.locality',tracking=True)
    origin_state_id = fields.Many2one('res.country.state', related="origin_locality_id.state_id")
    destination_locality_id = fields.Many2one('afip.locality',tracking=True)
    destination_state_id = fields.Many2one('res.country.state', related="destination_locality_id.state_id")
    
    commitment_date = fields.Datetime(tracking=True)
    start_date = fields.Datetime(tracking=True)
    arrived_date = fields.Datetime(tracking=True)
    end_date = fields.Datetime(tracking=True)
    
    distance = fields.Integer(tracking=True)
    delivered_cpe = fields.Integer(related="cpe_id.unload_net", string="Delivered CPE")
    delivered = fields.Integer()
    delivered_to_invoice =fields.Integer(_("To Invoice"),compute='_compute_delivered', readonly=True, tracking=True)
    delivered_diff = fields.Integer(_("Difference"), compute='_compute_delivered')
    delivered_total = fields.Integer()
    
    sale_line_id = fields.Many2one(
        'sale.order.line',
        string="Línea de Pedido",
        compute="_compute_sale_line_id",
        inverse="_inverse_sale_line_id",
        store=True,
        tracking=True
    )

    sale_id = fields.Many2one('sale.order', related='sale_line_id.order_id',readonly=True,store=True)
    price_unit = fields.Float(related="sale_line_id.price_unit")
    product_uom = fields.Many2one('uom.uom', related='sale_line_id.product_uom')
    rate_label = fields.Char(_("Rate"),compute="_compute_rate_label")
    
    cpe_id = fields.Many2one("afip.cpe","Carta de Porte",ondelete="set null")
    cpe_pdf = fields.Many2one('ir.attachment', related='cpe_id.pdf3')
    cpe_status_date = fields.Datetime(related = 'cpe_id.status_date')
    cpe_mismatch = fields.Boolean()
    
    driver_response = fields.Selection([ ('confirmed',_('Confirmed')),('rejected',_('Rejected') ) ], tracking=True)
    
    warnings = fields.Char()
    
    ### Compute methods
        
    @api.depends('cancelled','end_date','start_date','driver_id','driver_response','sale_id.state')
    def _compute_state(self):
        # TODO: revisar estados de CPE
        for record in self:
            old_state = record.state
            
            if record.sale_id.state == 'cancel':
                record.state = 'cancelled'
                
                if old_state != record.state:
                    message = _(
                        "Trip cancelled because sale order %s was cancelled", 
                        Markup(
                            f"""<a href=# data-oe-model=sale.order data-oe-id={record.sale_id.id}"""
                            f""">{record.sale_id.name}</a>"""
                        )
                    )
                    record.message_post(body=message)
                    
            elif record.cancelled:
                record.state='cancelled'
            elif record.end_date and record.driver_id:
                record.state = 'completed'
            elif record.start_date:
                record.state = 'started'
            elif record.driver_id and record.driver_response=='confirmed':
                record.state = 'confirmed'
            elif record.driver_id:
                record.state = 'assigned'
            else:
                record.state = 'draft'
            if old_state != record.state:
                self.env['bus.bus']._sendone('trucking','trucking_trip_changed',{'id':record.id,'order_id':record.sale_id.id})
        
    @api.depends('driver_id.vehicle_id')
    def _compute_vehicle_id(self):
        for record in self:
            if not record.state in ['completed','cancelled']:
                record.vehicle_id = record.driver_id.vehicle_id
            else:
                record.vehicle_id = record.vehicle_id

    @api.depends('customer_id')
    def _compute_contact_phone(self):
        for record in self:
            if not record.contact_phone:
                record.contact_phone = record.customer_id.mobile or record.customer_id.phone or False

    @api.depends('driver_id')
    def _compute_driver_phone(self):
        for record in self:
            if not record.driver_phone:
                record.driver_phone = record.driver_id.mobile or record.driver_id.phone or False
    
    @api.depends('state')
    def _compute_is_active(self):
        for record in self:
            record.is_active = record.state not in ['draft','completed','cancelled']
    
    @api.depends('delivered_cpe','delivered')
    def _compute_delivered(self):
        for record in self:
            record.delivered_to_invoice = record.delivered or record.delivered_cpe
            record.delivered_diff = record.delivered_cpe and record.delivered and record.delivered - record.delivered_cpe or 0
    
    @api.depends('sale_line_id')
    def _compute_sale_line_id(self):
        for record in self:
            line = self.env['sale.order.line'].search([('trucking_trip_id', '=', record.id)], limit=1)
            record.sale_line_id = line if line else False

    def _inverse_sale_line_id(self):
        for record in self:
            old_lines = self.env['sale.order.line'].search([('trucking_trip_id', '=', record.id)])
            if old_lines:
                old_lines.write({'trucking_trip_id': False})
            
            if record.sale_line_id:
                record.sale_line_id.trucking_trip_id = record.id
    
    @api.depends('price_unit','product_uom')
    def _compute_rate_label(self):
        for record in self:
            if record.price_unit:
                price = self.company_id.currency_id.format(record.price_unit)
                record.rate_label = _('%s per %s',price,record.product_uom.name)
            else:
                record.rate_label=False
    
    @api.onchange('vehicle_id', 'driver_id', 'is_active')
    def _onchange_check_availability(self):
        if not self.is_active:
            return

        domain = [('is_active', '=', True), ('id', '!=', self._origin.id)]
        warning_msg = ""

        # Verificar Camión
        if self.vehicle_id:
            conflict_truck_order = self.search(domain + [('vehicle_id', '=', self.vehicle_id.id)], limit=1)
            if conflict_truck_order:
                warning_msg += _("Vehicle %s is already active on order %s\n") % (
                    self.vehicle_id.display_name, conflict_truck_order.display_name or 'ID ' + str(conflict_truck_order.id)
                )

        # Verificar Conductor
        if self.driver_id:
            conflict_order = self.search(domain + [('driver_id', '=', self.driver_id.id)], limit=1)
            if conflict_order:
                warning_msg += _("Driver  %s is assigned to active order: %s\n",
                    self.driver_id.name, 
                    conflict_order.display_name or 'ID ' + str(conflict_order.id)
                )

        if warning_msg:
            return {
                'warning': {
                    'title': _("Resource currently busy"),
                    'message': _("Be aware that:\n\n") + warning_msg + 
                               _("\nYou can dismiss this message if this is a future assignment."),
                }
            }
            
    ### Model methods ###
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("trucking.trip")
        records = super(TruckingTrip, self).create(vals_list)
        print("create",records)
        for record in records:
            if record.sale_line_id.tms_order_ids:
                record._import_from_tms()
        return records
    
    
    def write(self, vals):
        ret = super().write(vals)
        if 'cpe_id' in vals and not self.env.context.get('trucking_clone',False):
            if self.cpe_id:
                updated = self.cpe_id.action_update_cpe()
                if not updated:
                    self.action_update_from_cpe()
            elif self.cpe_mismatch:
                self.cpe_mismatch=False
        
        if any(key in vals for key in ['state','driver_id','tag_ids','cpe_id','warnings']):
            print("sending trip_changed",self.id,self.sale_id)
            self.env['bus.bus']._sendone('trucking','trucking_trip_changed',{'id':self.id,'order_id':self.sale_id.id})
        if any(key in vals for key in ['state','distance','delivered','delivered_cpe']):
            self._update_sale_line()
            
        return ret
    
    def _import_from_tms(self):
        self.ensure_one()
        tms_order = self.sale_line_id.tms_order_ids[0]
        if not tms_order:
            _logger.warning(_("Line %s doesn't have a tms_order",self.sale_line_id))
            return
        driver_id = tms_order.driver_id and tms_order.driver_id.partner_id or False
        if driver_id and not driver_id.truck_driver:
            driver_id.truck_driver = True
            driver_id.vehicle_id = tms_order.driver_id.vehicle_id
        self.driver_id = driver_id
        self.vehicle_id = tms_order.vehicle_id
        self.trailer_id = tms_order.trailer_id
        self.commitment_date = tms_order.scheduled_date_start or self.sale_id.commitment_date
        self.start_date = tms_order.date_start
        self.end_date = tms_order.date_end
        self.distance = tms_order.distance
        self.delivered = tms_order.delivered_total
        
        
        self.cpe_id = tms_order.cpe_id
        if self.cpe_id and self.cpe_id.status != 'BR':
            print(self,"updating from cpe")
            self.action_update_from_cpe()
            
        message = _(
            "Trip cloned from: %s", 
            Markup(
                f"""<a href=# data-oe-model=tms.order data-oe-id={tms_order.id}"""
                f""">{tms_order.name}</a>"""
            )
        )
        self.message_post(body=message)
            
    def _convert_from_tms(self):
        for record in self:

            if not record.sale_line_id.cloned_line_id:
                print(record,": no tengo cloned line!")
                return
            
            tms_order = record.sale_line_id.cloned_line_id.tms_order_ids[0]
            
            if not tms_order:
                print(record,":",record.sale_line_id.cloned_line_id,"no tiene tms_order!")
                return
            
            driver_id = tms_order.driver_id and tms_order.driver_id.partner_id or False
            if driver_id and not driver_id.truck_driver:
                driver_id.truck_driver = True
                driver_id.vehicle_id = tms_order.driver_id.vehicle_id
            record.driver_id = driver_id
            record.cpe_id = tms_order.cpe_id
            
            record.commitment_date = tms_order.scheduled_date_start or record.commitment_date
            record.start_date = tms_order.date_start
            record.end_date = tms_order.date_end
            record.distance = tms_order.distance
            record.delivered = tms_order.delivered
            record.delivered_to_invoice = tms_order.delivered_extra and tms_order.delivered + tms_order.delivered_extra
            message = _(
                "Trip cloned from: %s", 
                Markup(
                    f"""<a href=# data-oe-model=tms.order data-oe-id={tms_order.id}"""
                    f""">{tms_order.name}</a>"""
                )
            )
            record.message_post(body=message)
            
    
    def action_update_from_cpe(self):
        for record in self:
            cpe = record.cpe_id
            if cpe.transport_ids:
                driver_id = cpe.transport_ids[0].driver_id
                if record.driver_id and driver_id != record.driver_id:
                    _logger.warning("CPE %s: Driver mismatch: %s (%s) != %s (%s) ",
                        record,
                        record.driver_id, 
                        record.driver_id.name,
                        driver_id,
                        driver_id.name
                    )
                    if not record.cpe_mismatch:
                        record.cpe_mismatch = True
                        message = _(
                            "Driver %s from CPE %s mismatches the one in the order (%s). The order was not updated.",
                            "%s (%s)" % (driver_id.name, driver_id.id,),
                            Markup(
                                f"""<a href=# data-oe-model=afip.cpe data-oe-id={record.cpe_id.id}"""
                                f""">{record.cpe_id.name}</a>"""
                            ),
                            "%s (%s)" % (record.driver_id.name, record.driver_id.id,),
                        )
                        self.with_user(SUPERUSER_ID).message_post(
                            body=message,
                            message_type='comment',
                        )
                    return False
                record.cpe_mismatch = False
                record.driver_id = cpe.transport_ids[0].driver_id
                record.vehicle_id = cpe.transport_ids[0].vehicle_id
                record.trailer_id = cpe.transport_ids[0].trailer_id
                record.start_date = cpe.transport_ids[0].start_date
                record.distance = cpe.transport_ids[0].distance
                
                #record.delivered_cpe = cpe.unload_net
                
                # If driver is on the CPE, update the confirmed status
                if not record.driver_response:
                    record.driver_response = 'confirmed'
                
                if cpe.status == 'CN':
                    record.state ='completed'
                    record.end_date = record.end_date or cpe.status_date
                elif cpe.status == 'CF':
                    record.state = 'arrived'
                    record.arrived_date = record.arrived_date or cpe.status_date
                elif cpe.status in ['AN','RE']:
                    record.state = 'cancelled'
                                    
            if cpe.customer_id:
                #record.customer_id = cpe.customer_id
                
                # TODO: check if partner_invoice_id is the same of other trips.
                record.sale_id.partner_invoice_id = cpe.customer_id                
            if cpe.origin_locality_id:
                record.origin_locality_id = cpe.origin_locality_id
            if cpe.destination_locality_id:
                record.destination_locality_id = cpe.destination_locality_id
            
            message = _(
                "Orden actualizada desde la carta de porte: %s",
                Markup(
                    f"""<a href=# data-oe-model=afip.cpe data-oe-id={record.cpe_id.id}"""
                    f""">{record.cpe_id.name}</a>"""
                ),
            )
            self.message_post(body=message)
    
    @api.model
    def assign_driver(self,trip_id,driver_id):
        trip = self.browse(trip_id)
        trip.driver_id = int(driver_id)
        print("Assigned driver %s to trip %s" % (driver_id,trip_id))
        message = _(
            "Driver assigned: %s",
            Markup(
                f"""<a href=# data-oe-model=res.partner data-oe-id={driver_id}"""
                f""">{trip.driver_id.name}</a>"""
            ),
        )
        trip.message_post(body=message)
        trip.driver_response = False
        return trip.id
    
    def unlink(self):
        for trip in self:
            if not trip.can_be_deleted():
                raise UserError(_(
                    "You can't delete a trip with information"
                    "Trip %s has information that can't be deleted. "
                    "You can cancel the trip or set it to draft and then delete it.",
                    trip.name
                ))
        return super(TruckingTrip, self).unlink()
    
    ### Bussiness logic ###    
    
    def can_be_deleted(self):
        """
        Determina si el viaje permite cambios estructurales desde la SO.
        Retorna True si está en borrador o si no tiene conductor y distancia 0.
        """
        self.ensure_one()
        # Regla: Estado draft O (Sin conductor Y sin distancia)
        return self.state == 'draft' or (not self.driver_id and self.distance == 0)

    def _update_sale_line(self):
        distance_uom = self.env.ref('uom.uom_categ_length')
        weight_uom = self.env.ref('uom.product_uom_categ_kgm')
        units_uom = self.env.ref('uom.product_uom_categ_unit')
        
        kg_uom = self.env.ref('uom.product_uom_kgm')
        km_uom = self.env.ref('uom.product_uom_km')
        for record in self:
            line = record.sale_line_id
            if not line:
                _logger.warning("Trucking trip %s is not associated with a sale order line",record.name)
                continue
            
            product_id = line.product_id
            
            if not product_id:
                product_id = self._default_product()
                _logger.warning("Trucking trip %s order line %s of sale order %s doesn't have a product. Setting %s to it",record.name,line.id,record.sale_id,product_id.name)
                line.product_id = product_id
            
            if record.state == 'cancelled':
                line.qty_delivered = 0
                line.product_uom = product_id.uom_id
                line.product_uom_qty = line.qty_delivered
                continue
            
            line.distance = record.distance
            
            if product_id.uom_id.category_id == weight_uom:
                line.qty_delivered = kg_uom._compute_quantity(record.delivered_to_invoice,product_id.uom_id)
                
            elif product_id.uom_id.category_id == distance_uom:
                line.qty_delivered = km_uom._compute_quantity(record.distance,product_id.uom_id)
            elif product_id.uom_id.category_id == units_uom:
                line.qty_delivered = (record.distance and record.delivered_to_invoice) and 1 or 0
            
            line.product_uom = product_id.uom_id or units_uom
            line.product_uom_qty = line.qty_delivered
            line.name = f'{record.name} {record.driver_id.display_name}'
            print("_update_sale_line of",record, line.name,line.product_id,line.product_uom.name)

    ### Actions ###
    
    def action_view_sales(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_line_id.order_id.id or self.sale_id.id,
            "context": {"create": False},
            "name": _("Sales Orders"),
        }
    def action_open_trip_form(self):
        return {
            'name': _('Trip Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'trucking.trip', # Asegúrate que sea tu modelo
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current', # Esto es la clave para que no sea modal
        }
    def action_cancel_trip(self):
        for record in self:
            record.cancelled = True
        return True
    
    def action_enable_trip(self):
        for record in self:
            record.cancelled = False
        return True
    
    def action_end_trip(self):
        trips_to_end = self.filtered(lambda t: t.state == 'started')
        trips_to_end.end_date = datetime.now()
        return len(trips_to_end) > 0
    
    def action_confirm_driver(self):
        self.ensure_one()
        if not self.driver_response == 'confirmed':
            self.driver_response='confirmed'
            return True
        return False
        
    def action_start_trip(self):
        trips_to_start = self.filtered(lambda t: t.state in ['assigned','confirmed'])
        trips_to_start.driver_response='confirmed'
        trips_to_start.start_date = datetime.now()
        return len(trips_to_start) > 0
    
    
        
    ### Whatsapp Integration ###
        
    def _whatsapp_get_partner(self):
        if "customer_id" in self._fields:
            return self.customer_id
        return super()._whatsapp_get_partner()
    
    def _send_whatsapp(self,partner_id,body=False,template_id=False,gateway=1):
        gateway_id = self.env['mail.gateway'].browse(gateway)
        context = {'default_res_id':self.id}
        if template_id:
            context['whatsapp_template_id'] = template_id
            template = self.env['mail.whatsapp.template'].browse(template_id)    
            body = template.with_context(context).render_body_message()
            
        number_field_name = partner_id.mobile and 'mobile' or 'phone'
        channel = partner_id._whatsapp_get_channel(number_field_name, gateway_id)
        message = channel.with_context(context).message_post(
            body=body, subtype_xmlid="mail.mt_comment", message_type="comment")
        message.trucking_trip_id = self.id
        _logger.info("WA %s sent to %s:  %s",self.name,partner_id.name,message)
            
    def action_send_whatsapp_request(self):
        partner = self.driver_id
        #partner = self.env['res.partner'].browse(4185) # YO
        self._send_whatsapp(partner,template_id=12)

    