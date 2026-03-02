from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from markupsafe import Markup

import logging

_logger = logging.getLogger(__name__)

class TruckingTrip(models.Model):
    _name = 'trucking.trip'
    _description = 'Trucking Trip'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    
    state = fields.Selection([
        ('draft','Draft'),
        ('assigned','Assigned'),
        ('confirmed','Confirmed'),
        ('started','Started'),
        ('arrived','Arrived'),
        ('completed','Completed'),
        ('cancelled','Cancelled',)
        
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
        compute="_compute_driver_id", store=True, readonly=False, tracking=True, domain=[('truck_driver','=',True)]
    )
    
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string="Camión",
        compute="_compute_vehicle_id", store=True, readonly=False,
        domain=[('vehicle_type', '=', 'truck')], tracking=True
    )

    trailer_id = fields.Many2one(
        related='vehicle_id.trailer_id', string="Trailer",
        store=True, readonly=True
    )

    contact_phone = fields.Char(compute = '_compute_contact_phone')
    driver_phone =  fields.Char(compute='_compute_driver_phone')
    
    
    origin_locality_id = fields.Many2one('afip.locality',tracking=True)
    origin_state_id = fields.Many2one('res.country.state', related="origin_locality_id.state_id")
    destination_locality_id = fields.Many2one('afip.locality',tracking=True)
    destination_state_id = fields.Many2one('res.country.state', related="destination_locality_id.state_id")
    
    commitment_date = fields.Datetime(tracking=True)
    start_date = fields.Datetime(tracking=True)
    end_date = fields.Datetime(tracking=True)
    
    distance = fields.Integer(tracking=True)
    delivered = fields.Integer()
    delivered_extra =fields.Integer()
    delivered_total = fields.Integer(compute='_compute_delivered', readonly=True, tracking=True)

    
    sale_line_id = fields.Many2one(
        'sale.order.line',
        string="Línea de Pedido",
        compute="_compute_sale_line_id",
        inverse="_inverse_sale_line_id",
        store=True,
        tracking=True
    )

    sale_id = fields.Many2one('sale.order', related='sale_line_id.order_id',readonly=True,store=True)
    
    cpe_id = fields.Many2one("afip.cpe","Carta de Porte",ondelete="set null")
    cpe_mismatch = fields.Boolean()
    
    driver_response = fields.Selection([ ('confirmed',_('Confirmed')),('rejected',_('Rejected') ) ])
    
    warnings = fields.Char()
    
    ### Compute methods
    
    @api.depends('cancelled','end_date','start_date','driver_id','driver_response')
    def _compute_state(self):
        # TODO: revisar estados de CPE
        for record in self:
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
            
    @api.depends('vehicle_id.driver_id')
    def _compute_driver_id(self):
        for record in self:
            record.driver_id = record.vehicle_id.driver_id
            print(record,"setting driver",record.driver_id)

    @api.depends('driver_id.vehicle_id')
    def _compute_vehicle_id(self):
        for record in self:
            record.vehicle_id = record.driver_id.vehicle_id
            print(record,"setting vehicle",record.vehicle_id)
            #if record.driver_id:
            # vehicle = self.env['fleet.vehicle'].search([
            #     ('driver_id', '=', record.driver_id.id),
            #     ('vehicle_type', '=', 'truck')
            # ], limit=1)
            # if vehicle:
            #     record.vehicle_id = vehicle


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
    
    @api.depends('delivered','delivered_extra','cpe_id')
    def _compute_delivered(self):
        for record in self:
            record.delivered_total = record.delivered + record.delivered_extra
    
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
            if driver_id:
                driver_id.truck_driver = True
                tms_order.driver_id.vehicle_id.driver_id = driver_id
            record.driver_id = driver_id
            record.cpe_id = tms_order.cpe_id
            
            record.commitment_date = tms_order.scheduled_date_start or record.commitment_date
            record.start_date = tms_order.date_start
            record.end_date = tms_order.date_end
            record.distance = tms_order.distance
            record.delivered = tms_order.delivered
            record.delivered_extra = tms_order.delivered_extra
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
    
    def unlink(self):
        for record in self:
            if not record.state == 'draft':
                raise UserError(_(
                    "No se puede eliminar el viaje '%s' porque contiene datos. "
                    "Primero debe desactivarlo."
                ) % record.display_name)
        return super(TruckingTrip, self).unlink()
    
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

    