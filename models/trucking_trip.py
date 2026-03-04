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
        'res.partner', string="Conductor",
        tracking=True, domain=[('truck_driver','=',True)]
    )
    
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string="Camión",
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
    delivered_cpe = fields.Integer(related="cpe_id.unload_net")
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
    
    @api.depends('cancelled','end_date','start_date','driver_id','driver_response')
    def _compute_state(self):
        # TODO: revisar estados de CPE
        for record in self:
            old_state = record.state
            if record.cancelled:
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

            
    # @api.depends('vehicle_id.driver_id')
    # def _compute_driver_id(self):
    #     for record in self:
    #         record.driver_id = record.vehicle_id.driver_id
    #         print(record,"setting driver",record.driver_id)

    @api.depends('driver_id.vehicle_id')
    def _compute_vehicle_id(self):
        for record in self:
            if not record.state in ['completed','cancelled']:
                record.vehicle_id = record.driver_id.vehicle_id
                print(record,"setting vehicle",record.vehicle_id)
            else:
                record.vehicle_id = record.vehicle_id
                print("not changing vehicle of trip",self,self.state)


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
            # Buscamos la línea que apunta a este registro específico
            line = self.env['sale.order.line'].search([('trucking_trip_id', '=', record.id)], limit=1)
            record.sale_line_id = line if line else False

    def _inverse_sale_line_id(self):
        for record in self:
            # 1. Liberamos cualquier línea que tuviera este viaje asignado previamente
            old_lines = self.env['sale.order.line'].search([('trucking_trip_id', '=', record.id)])
            if old_lines:
                old_lines.write({'trucking_trip_id': False})
            
            # 2. Escribimos el ID del viaje en la nueva línea seleccionada
            if record.sale_line_id:
                record.sale_line_id.trucking_trip_id = record.id
    
    @api.depends('price_unit','product_uom')
    def _compute_rate_label(self):
        for record in self:
            if record.price_unit:
                price = self.company_id.currency_id.format(record.price_unit)
                record.rate_label = _(f'{price} per {record.product_uom.name}')
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
            conflict_truck = self.search(domain + [('vehicle_id', '=', self.vehicle_id.id)], limit=1)
            if conflict_truck:
                warning_msg += _("- El camión %s ya está en la orden activa: %s\n") % (
                    self.vehicle_id.display_name, conflict_truck.display_name or 'ID ' + str(conflict_truck.id)
                )

        # Verificar Conductor
        if self.driver_id:
            conflict_driver = self.search(domain + [('driver_id', '=', self.driver_id.id)], limit=1)
            if conflict_driver:
                warning_msg += _("- El conductor %s ya está en la orden activa: %s\n") % (
                    self.driver_id.name, conflict_driver.display_name or 'ID ' + str(conflict_driver.id)
                )

        if warning_msg:
            return {
                'warning': {
                    'title': _("Recurso actualmente ocupado"),
                    'message': _("Ten en cuenta que:\n\n") + warning_msg + 
                               _("\nPuedes continuar si esta es una asignación futura."),
                }
            }
            
    ### Model methods ###
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("trucking.trip")
        return super(TruckingTrip, self).create(vals_list)
    
    def write(self, vals):
        ret = super().write(vals)
        if any(key in vals for key in ['state','driver_id','tag_ids','cpe_id','warnings']):
            print("sending trip_changed",self.id,self.sale_id)
            self.env['bus.bus']._sendone('trucking','trucking_trip_changed',{'id':self.id,'order_id':self.sale_id.id})
        return ret
    
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
            if tms_order.stage_id == self.env.ref("tms.tms_stage_order_cancelled"):
                record.cancelled = True
    
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
                            f'{driver_id.name} ({driver_id.id})',
                            Markup(
                                f"""<a href=# data-oe-model=afip.cpe data-oe-id={record.cpe_id.id}"""
                                f""">{record.cpe_id.name}</a>"""
                            ),
                            f'{record.driver_id.name} ({record.driver_id.id})',
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
                record.customer_id = cpe.customer_id
                
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
        """ 
        Impedir el borrado si el viaje ya tiene gestión operativa.
        Este método se activará incluso si se borra la Sale Order Line 
        gracias al ondelete='cascade'.
        """
        for trip in self:
            if not trip.can_be_deleted():
                raise UserError(
                    f"No se puede eliminar el viaje '{trip.name}'. "
                    "Ya cuenta con conductor asignado o datos de ruta confirmados."
                )
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
        message.tms_order_id = self.id
        _logger.info("WA %s sent to %s:  %s",self.name,partner_id.name,message)
            
    def action_send_whatsapp_request(self):
        partner = self.driver_id
        #partner = self.env['res.partner'].browse(4185) # YO
        self._send_whatsapp(partner,template_id=12)

    