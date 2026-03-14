from odoo import _, api, fields, models

class AfipCPE(models.Model):
    _inherit = 'afip.cpe'
    trucking_trip_ids = fields.One2many('trucking.trip','cpe_id') 
    trucking_trip_id = fields.Many2one('trucking.trip', compute='_compute_trucking_trip_id', tracking=True,store=True)
    
    @api.depends('trucking_trip_ids')
    def _compute_trucking_trip_id(self):
        for record in self:
            # clean
            trip = record.trucking_trip_ids.filtered(lambda t: t.cpe_id == record)
            record.trucking_trip_id = trip and trip[0] or False
            if record.trucking_trip_id:
                # is this necesary?
                record.trucking_trip_id._update_from_cpe()
    
    def _get_driver(self, cuit, name=None):
        ret = super()._get_driver(cuit, name)
        if ret and not ret.truck_driver:
            ret.truck_driver = True
        return ret
    
    def action_update_cpe(self, force=False):
        ret = super().action_update_cpe(force=force)
        
        if self.trucking_trip_id:
            self.trucking_trip_id._update_from_cpe()
        return ret
    
    def action_view_trucking_trip(self):
        
        if self.trucking_trip_id:
            action = self.env["ir.actions.act_window"]._for_xml_id(
            "trucking.action_trucking_trips")
            action["views"] = [(self.env.ref("trucking.trucking_trip_view_form").id, "form")]
            action["res_id"] = self.trucking_trip_id.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action
    
    def write(self, vals):
        res = super().write(vals)
        # Si cambia el nombre Y tiene al menos un viaje asociado...
        if 'name' in vals:
            for reg in self:
                if reg.trucking_trip_ids: 
                    reg.action_update_cpe()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # En la creación es raro que ya tenga el trip_id seteado 
        # (salvo que lo pases en el vals), pero por las dudas:
        for reg in records:
            if reg.trucking_trip_ids:
                reg.action_update_cpe()
        return records
    
class AfipLocality(models.Model):
    _inherit="afip.locality"
    _order = "trucking_trip_count desc, afip_state_id, name"
    
    trucking_trip_ids = fields.Many2many('trucking.trip', compute='_compute_trucking_trips')
    trucking_trip_origin_ids = fields.One2many('trucking.trip', 'origin_locality_id')
    trucking_trip_destination_ids = fields.One2many('trucking.trip', 'destination_locality_id')
    trucking_trip_count = fields.Integer(compute = '_compute_trucking_trip_count', store=True)
    
    @api.depends('trucking_trip_origin_ids', 'trucking_trip_destination_ids')
    def _compute_trucking_trips(self):
        for record in self:
            record.trucking_trip_ids = record.trucking_trip_origin_ids + record.trucking_trip_destination_ids
    
    @api.depends('trucking_trip_origin_ids', 'trucking_trip_destination_ids')
    def _compute_trucking_trip_count(self):
        for record in self:
            record.trucking_trip_count = len(record.trucking_trip_origin_ids) + len(record.trucking_trip_destination_ids)