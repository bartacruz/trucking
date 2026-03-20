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
        inverse='_inverse_trailer_id',
    )
    
    # Referencia Inversa: Trailer -> Camión
    truck_id = fields.Many2one(
        'fleet.vehicle',
        string="Truck",
        domain=[('vehicle_type', '=', 'truck')],
        inverse='_inverse_truck_id',
    )
    
    truck_driver_id = fields.Many2one('res.partner', related="truck_id.driver_id", store=True)

    _sql_constraints = [
        ('trailer_unique', 'unique(trailer_id)', '¡Este trailer ya está asignado a otro camión!'),
        ('driver_unique', 'unique(driver_id)', '¡Este conductor ya tiene un vehículo asignado!')
    ]

    def _inverse_trailer_id(self):
        for record in self:
            if record.trailer_id:
                record.trailer_id.truck_id = record
                old_trucks = self.env['fleet.vehicle'].search([
                    ('trailer_id', '=', record.trailer_id.id),
                    ('id', '!=', record.id)
                ])
                old_trucks.trailer_id= False
                print("_inverse_trailer_id SET",record.name,record.trailer_id.name,old_trucks.mapped('name'))
            else:
                # Unset trailer search for trailers that have me as a truck
                old_trailers = self.env['fleet.vehicle'].search([
                    ('truck_id', '=', record.id),
                ])
                old_trailers.truck_id = False
                print("_inverse_trailer_id DEL",record.name,old_trailers.mapped('name'))
    
    def _inverse_truck_id(self):
        for record in self:
            if record.truck_id:
                record.truck_id.trailer_id = record
                old_trailers = self.env['fleet.vehicle'].search([
                    ('truck_id', '=', record.truck_id.id),
                    ('id', '!=', record.id)
                ])
                old_trailers.truck_id= False
                
                print("_inverse_truck_id SET",record.name,record.truck_id.name,old_trailers.mapped('name'))
            else:
                # Unset truck search for trucks that have me as a trailer
                old_trucks = self.env['fleet.vehicle'].search([
                    ('trailer_id', '=', record.id),
                ])
                old_trucks.trailer_id = False
                print("_inverse_truck_id DEL",record.name,old_trucks.mapped('name'))
            
    @api.onchange('trailer_id')
    def _onchange_trailer_id(self):
        if self.vehicle_type == 'truck' and self.trailer_id:
            if self.trailer_id.truck_id and self.trailer_id.truck_id != self:
                return {
                    'warning': {
                        'title': "Aviso de Reasignación",
                        'message': f"El trailer {self.trailer_id.name} ya está asignado al camión {self.trailer_id.truck_id.name}. "
                                f"Si guarda, se desvinculará del camión anterior.",
                    }
                }
    @api.onchange('tuck_id')
    def _onchange_truck_id(self):
        if self.vehicle_type == 'trailer' and self.truck_id:
            if self.truck_id.trailer_id and self.truck_id.trailer_id != self:
                return {
                    'warning': {
                        'title': "Aviso de Reasignación",
                        'message': f"El camión {self.truck_id.name} ya está asignado al trailer {self.truck_id.trailer_id.name}. "
                                f"Si guarda, se desvinculará del trailer anterior.",
                    }
                }
    
    # def _inverse_truck_id(self):
    #     for record in self:
    #         if record.truck_id:
    #             old_trailers = record.search([('truck_id', '=', record.truck_id.id),('id', '!=', record._origin.id)])
    #             old_trailers.truck_id = False
    #             record.truck_id.trailer_id = record
    #             print("_inverse_truck_id SET",record.name,record.truck_id.name,old_trailers.mapped('name'))
    #         else:
    #             old_trucks = record.search([('trailer_id', '=', record.id)])
    #             old_trucks.trailer_id= False
    #             print("_inverse_truck_id DEL",record.name,old_trucks.mapped('name'))
    
    # def _inverse_trailer_id(self):
    #     for record in self:
    #         if record.trailer_id:
    #             old_trucks = record.search([('trailer_id', '=', record.trailer_id.id),('id', '!=', record._origin.id)])
    #             old_trucks.trailer_id = False
    #             record.trailer_id.truck_id = record
    #             print("_inverse_trailer_id SET",record.name,record.trailer_id.name,old_trucks.mapped('name'))
    #         else:
    #             old_trailers = record.search([('truck_id', '=', record.id)])
    #             print("antes de borrar",old_trailers.truck_id)
    #             old_trailers.truck_id = False
    #             print("_inverse_trailer_id DEL",record.name,old_trailers.mapped('name'))
        
    @api.depends('trailer_id')
    def _compute_truck_id(self):
        print("_compute_truck_id",self)
        for record in self:
            # if not record.truck_ids:
            #     record.truck_id = False
            # else:
            #     print("_compute_truck_id",record.truck_ids.mapped('name'),record._origin.truck_ids.mapped('name'))
            #     record.truck_id = record.truck_ids[0]
            if record.trailer_id:
                old_trucks = record.search([('trailer_id', '=', record.trailer_id.id),('id', '!=', record._origin.id)])
                old_trucks.trailer_id = False
                print("updating trailer",record.name,record.trailer_id.name,old_trucks.mapped('name'))
                record.trailer_id.truck_id = record
            else:
                old_trailers = record.search([('truck_id', '=', record.id)])
                print("deleting trailer",record.name,old_trailers.mapped('name'))
                old_trailers.truck_id = False
                
                
