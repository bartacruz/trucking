from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class TruckingTrip(models.Model):
    _name = 'trucking.trip'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    state = fields.Selection([
        ('draft','Draft'),
        ('assigned','Assigned'),
        ('confirmed','Confirmed'),
        ('started','Started'),
        ('arrived','Arrived'),
        ('completed','Completed'),
        ('cancelled','Cancelled',)
    ])
    is_active = fields.Boolean(compute='_compute_is_active', store=True)
    
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
    
    customer_id = fields.Many2one("res.partner", _("Customer"), related="sale_order_id.partner_shipping_id", store=True, tracking=True)
    
    driver_id = fields.Many2one(
        'res.partner', string="Conductor",
        compute="_compute_driver_id", store=True, readonly=False, tracking=True, domain=[('trucking_driver','=',True)]
    )
    
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string="Camión",
        compute="_compute_vehicle_id", store=True, readonly=False,
        domain=[('vehicle_type', '=', 'truck')], tracking=True
    )

    trailer_id = fields.Many2one(
        related='vehicle_id.trailer_id', string="Trailer Relacionado",
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

    
    sale_order_line_id = fields.Many2one('sale.order.line',tracking = True)
    sale_order_id = fields.Many2one('sale.order', related='sale_order_line_id.order_id',readonly=True)
    
    cpe_id = fields.Many2one("afip.cpe","Carta de Porte",ondelete="set null")
    cpe_mismatch = fields.Boolean()
    

    @api.depends('vehicle_id')
    def _compute_driver_id(self):
        for record in self:
            if record.vehicle_id and record.vehicle_id.driver_id:
                record.driver_id = record.vehicle_id.driver_id

    @api.depends('driver_id')
    def _compute_vehicle_id(self):
        for record in self:
            vehicle = self.env['fleet.vehicle'].search([
                ('driver_id', '=', record.driver_id.id),
                ('vehicle_type', '=', 'truck')
            ], limit=1)
            if vehicle:
                record.vehicle_id = vehicle


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
