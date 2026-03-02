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

    # Relación: Camión -> Trailer
    trailer_id = fields.Many2one(
        'fleet.vehicle', 
        string="Trailer Acoplado",
        domain=[('vehicle_type', '=', 'trailer')],
        tracking=True,
        help="Selecciona el trailer que está enganchado a este camión."
    )

    # Referencia Inversa: Trailer -> Camión
    truck_id = fields.Many2one(
        'fleet.vehicle',
        string="Camión Actual",
        compute="_compute_truck_id",
        store=True,
        help="Muestra el camión al que este trailer está acoplado actualmente."
    )

    _sql_constraints = [
        ('trailer_unique', 'unique(trailer_id)', '¡Este trailer ya está asignado a otro camión!')
    ]

    @api.depends('trailer_id')
    def _compute_truck_id(self):
        for record in self:
            # Buscamos qué registro tiene a 'record' asignado en su campo trailer_id
            parent = self.search([('trailer_id', '=', record.id)], limit=1)
            record.truck_id = parent if parent else False
