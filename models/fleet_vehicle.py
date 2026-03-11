from odoo import models, fields, api

class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    # Extendemos el campo original para definir los tipos
    vehicle_type = fields.Selection(
        selection_add=[('truck', 'Camión'), ('trailer', 'Trailer')],
        ondelete={'truck': 'cascade', 'trailer': 'cascade'}
    )

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    
    vehicle_type = fields.Selection(related='model_id.vehicle_type', store=True)
    
    # Relación: Camión -> Trailer
    trailer_id = fields.Many2one(
        'fleet.vehicle', 
        string="Trailer",
        domain=[('vehicle_type', '=', 'trailer')],
        tracking=True,
    )

    # Referencia Inversa: Trailer -> Camión
    truck_id = fields.Many2one(
        'fleet.vehicle',
        string="Truck",
        compute="_compute_truck_id",
        store=True,
    )
    
    truck_driver_id = fields.Many2one('res.partner', related="truck_id.driver_id", store=True)

    _sql_constraints = [
        ('trailer_unique', 'unique(trailer_id)', '¡Este trailer ya está asignado a otro camión!'),
        ('driver_unique', 'unique(driver_id)', '¡Este conductor ya tiene un vehículo asignado!')
    ]

    @api.depends('trailer_id')
    def _compute_truck_id(self):
        for record in self:
            if record.trailer_id:
                old_trucks = record.search([('trailer_id', '=', record.trailer_id.id),('id', '!=', record._origin.id)])
                old_trucks.trailer_id = False
                print("updating trailer",record.name,record.trailer_id.name,old_trucks.mapped('name'))
                record.trailer_id.truck_id = record
            else:
                old_trailers = record.search([('truck_id', '=', record.id)])
                print("deleting trailer",record.name,old_trailers.mapped('name'))
                old_trailers.truck_id = False
                
                
