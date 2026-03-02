from odoo import _, api, fields, models

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
