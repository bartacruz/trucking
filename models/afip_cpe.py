from odoo import _, api, fields, models

class AfipCPE(models.Model):
    _inherit = 'afip.cpe'
    trucking_trip_ids = fields.One2many('trucking.trip','cpe_id') 
    trucking_trip_id = fields.Many2one('trucking.trip', compute='_compute_trucking_trip_id')
    trucking_has_trip = fields.Boolean(compute="_compute_trucking_trip_id", store=True)
    
    @api.depends('trucking_trip_ids')
    def _compute_trucking_trip_id(self):
        for record in self:
            if not record.trucking_trip_ids:
                record.trucking_trip_id=False
                record.trucking_has_trip=False
                continue
            trip_id = self.trucking_trip_ids[0]
            #trip_id = self.env['trucking.trip'].search([ ('cpe_id','=',record.id) ],limit=1)
            record.trucking_trip_id = trip_id
            record.trucking_has_trip = len(trip_id) > 0
    
    def action_update_cpe(self, force=False):
        ret = super().action_update_cpe(force=force)
        if ret and self.trucking_trip_id:
            self.trucking_trip_id.action_update_from_cpe()
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