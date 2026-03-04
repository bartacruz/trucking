from odoo import _, api, fields, models
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    truck_driver = fields.Boolean(_('Truck driver'))
    
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Vehículo Asignado",
        compute="_compute_vehicle_id",
        inverse="_inverse_vehicle_id",
        store=True,
        ondelete='set null',
        tracking=True,
        help="Vehículo vinculado a este contacto a través del campo 'Conductor' en Flota."
    )
    trailer_id = fields.Many2one(
        'fleet.vehicle',
        related='vehicle_id.trailer_id'
    )
    trucking_state = fields.Selection([
        ('available','Available'),
        ('assigned','Assigned'),
        ('unavailable','Unavailable'),
        ],
        group_expand="_read_group_trucking_states",
        compute = '_compute_trucking_state',
        store=True,
        readonly=False,
        tracking=True
    )
    
    trucking_is_active = fields.Boolean()
    
    # Relación inversa necesaria para el cómputo
    trucking_trip_ids = fields.One2many(
        'trucking.trip', 
        'driver_id', 
        string="Historial de Viajes"
    )

    # Campo para el contador del Smart Button
    trucking_trip_count = fields.Integer(
        string="Cant. de Viajes", 
        compute="_compute_trucking_trip_count"
    )

    # Campo computado con su dependencia automática
    active_trucking_trip_id = fields.Many2one(
        'trucking.trip',
        string="Viaje Activo",
        compute="_compute_active_trucking_trip_id",
        store=True,
        index=True
    )
    
    active_trucking_trip_state = fields.Selection(
        related='active_trucking_trip_id.state',
        string="Estado del Viaje Activo",
        store=False
    )
    
    # For kanban sorting
    trucking_sequence = fields.Integer(string="Secuencia", default=10, copy=False)
    
    # For drivers list sorting
    trucking_state_sequence = fields.Integer(
        string="Secuencia de Estado",
        compute='_compute_trucking_state_sequence',
        store=True,
        index=True  # Indexado para que el order sea rapidísimo
    )
    
    def write(self, values):
        old_states = {p.id: p.trucking_state for p in self}
        ret = super().write(values)
        changed = self.filtered(lambda p: p.trucking_state != old_states.get(p.id))
        # TODO: make _trucking_state_updated multi, and call changed._trucking_state_updated.
        for record in changed:
            record._trucking_state_updated()
    
    
    @api.depends('trucking_state')
    def _compute_trucking_state_sequence(self):
        # Mapeo lógico: Available (1) -> Assigned (2) -> Unavailable (3)
        mapping = {
            'available': 1,
            'assigned': 2,
            'unavailable': 3,
        }
        for record in self:
            if record.trucking_state != record._origin.trucking_state:
                record.trucking_state_sequence = mapping.get(record.trucking_state, 9)
                print("partner state sequence changed",record)
                self._notify_trucking_update()

    @api.depends('active_trucking_trip_id','trucking_trip_ids','truck_driver')
    def _compute_trucking_state(self):
        for record in self:
            print('actualizando trucking_state',record)
            print(record.name,record.active_trucking_trip_id,record.trucking_state)
            if record.trucking_state == 'assigned' and not record.active_trucking_trip_id:
                record.trucking_state = 'available'
            elif record.trucking_state != 'assigned' and record.active_trucking_trip_id:
                record.trucking_state = 'assigned'
            else:
                # keep the state if set or if it's a driver, set to unavailable
                record.trucking_state = record.trucking_state or record.truck_driver and 'unavailable' or False
                
            if record.trucking_state != record._origin.trucking_state:
                print("llamando a _trucking_state_updated",record)
                record._trucking_state_updated()
                
        
    @api.depends('trucking_trip_ids')
    def _compute_trucking_trip_count(self):
        for record in self:
            record.trucking_trip_count = len(record.trucking_trip_ids)
            

    @api.depends('trucking_trip_ids.is_active')
    def _compute_active_trucking_trip_id(self):
        for record in self:
            # Filtramos en memoria los viajes del conductor que estén activos
            active_trip = record.trucking_trip_ids.filtered(lambda t: t.is_active)
            # Tomamos el primero si existe, de lo contrario False
            record.active_trucking_trip_id = active_trip[0] if active_trip else False
            

    @api.depends('vehicle_id')
    def _compute_vehicle_id(self):
        for record in self:
            # Buscamos el vehículo donde este partner es el driver_id
            vehicle = self.env['fleet.vehicle'].search([('driver_id', '=', record.id)], limit=1)
            record.vehicle_id = vehicle if vehicle else False

    def _inverse_vehicle_id(self):
        for record in self:
            # 1. Buscamos vehículos que tengan a este partner como conductor y los liberamos
            # (Para asegurar que el partner solo tenga un vehículo a la vez)
            old_vehicles = self.env['fleet.vehicle'].search([('driver_id', '=', record.id)])
            if old_vehicles:
                old_vehicles.write({'driver_id': False})
            
            # 2. Si se seleccionó un nuevo vehículo en la ficha del contacto,
            # le asignamos este partner como su conductor oficial
            if record.vehicle_id:
                record.vehicle_id.driver_id = record.id

    @api.model
    def _read_group_trucking_states(self, stages, domain, order):
        """
        Este método devuelve todas las opciones del Selection para que 
        aparezcan como columnas en el Kanban, incluso si están vacías.
        """
        # Retornamos la lista de claves del Selection
        return [key for key, val in self._fields['trucking_state'].selection]    
        
    ### Notifications ###
    
    def _notify_trucking_update(self, partner_ids=False):
        partners = self.browse(partner_ids or self)
        notifications = []
        for partner in partners:
            payload = {
                'id': partner.id,
            }
            notifications.append((
                'trucking',
                'trucking_driver_changed',
                payload
            ))
        print("_notify_trucking_update",notifications)
        self.env['bus.bus']._sendmany(notifications)
     
    def _trucking_state_updated(self):
        self.ensure_one()
        try:
            # If driver is made available, must go to the end of the queue
            if self.trucking_state == 'available':
                last_available = self.env['res.partner'].search([
                    ('trucking_state', '=', 'available'),
                    ('truck_driver', '=', True),
                    ('id', '!=', self.id)
                ], order='trucking_sequence desc', limit=1)
                self.trucking_sequence = (last_available.trucking_sequence + 1) if last_available else 10

            if self.trucking_state == 'assigned':
                if not self.active_trucking_trip_id:
                    raise UserError("No podés asignar un conductor sin un viaje activo. "
                                    "Por favor, usá el botón de 'Asignar Viaje' en la tarjeta.")
        except:
            _logger.exception("_trucking_state_updated %s" % self)
        self._notify_trucking_update()
        
    ### Actions ###
    
    def action_view_trucking_trips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Viajes de Transporte',
            'view_mode': 'tree,form',
            'res_model': 'trucking.trip',
            'domain': [('driver_id', '=', self.id)],
            # Forzamos que los activos (is_active=True) aparezcan primero, 
            # y luego por ID descendente (los más nuevos arriba)
            'context': {
                'default_driver_id': self.id,
                'default_order': 'is_active desc, id desc'
            },
        }
