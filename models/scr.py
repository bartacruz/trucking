for d in env['tms.driver'].search([]):
    print(d,d.name,d.partner_id,d.partner_id.name)
    d.partner_id.truck_driver = True
    d.partner_id.vehicle_id = d.vehicle_id
    
o = env['sale.order'].browse(22)
o.action_trucking_clone_tms()

for o in env['sale.order'].search([ ('has_tms_order','=',True),('has_trucking_trips','=',False) ]):
    o.action_trucking_clone_tms()
    env.cr.commit()
tms in env['tms.order'].search([ ('is_cancelled','=',True)])

sales = env['sale.order'].search([])
completed = sales.filtered(lambda s: s.state != 'cancel').filtered(lambda s: all(t.state in ['completed','cancelled'] for t in s.trucking_trip_ids))

for o in completed.filtered(lambda O: O.state != 'sale'):
    o.state = 'sale'
    
draft = sales.filtered(lambda s: s.state != 'cancel').filtered(lambda s: all(t.state in ['draft','assigned','cancelled'] for t in s.trucking_trip_ids))
for o in draft.filtered(lambda O: O.state != 'draft'):
    o.state = 'draft'

for o in sales:
     print(o,o.state,o.invoice_status,[t.state for t in o.trucking_trip_ids])