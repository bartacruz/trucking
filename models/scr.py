# Parar el cron de CPE
# Instalar Trucking (Camiones)
# Cambiar el web responsive por el de OCA

# Usuarios -> Conductores
for d in env['tms.driver'].search([]):
    print(d,d.name,d.partner_id,d.partner_id.name)
    d.partner_id.truck_driver = True
    d.partner_id.vehicle_id = d.vehicle_id
    env.cr.commit()
    
# Crear Trip product
env['product.template'].create({
    'name':'por Tonelada',
    'detailed_type': 'service',
    'invoice_policy':'delivery',
    'uom_id': env.ref('uom.product_uom_ton').id,
    'uom_po_id': env.ref('uom.product_uom_ton').id,
    'trucking_trip':True,
    'categ_id':4,
    'property_account_income_id':372,
})

# Clonar Trips en la misma orden de venta (y en la misma linea de la orden)
for o in env['sale.order'].search([ ('has_tms_order','=',True),('has_trucking_trips','=',False) ],order='id'):
    o.action_trucking_clone_tms()
    env.cr.commit()
    
# Eliminar las referencias a la orden de venta en tms.order
for tms in env['tms.order'].search([]):
    tms.tms_clone()
env.cr.commit()
    
# Cambiar el estado de las ordenes de venta segun el estado de los viajes
sales = env['sale.order'].search([])
completed = sales.filtered(lambda s: s.state != 'cancel').filtered(lambda s: all(t.state in ['completed','cancelled'] for t in s.trucking_trip_ids))

for o in completed.filtered(lambda O: O.state != 'sale'):
    o.state = 'sale'
env.cr.commit()
    
draft = sales.filtered(lambda s: s.state != 'cancel').filtered(lambda s: all(t.state in ['draft','assigned','cancelled'] for t in s.trucking_trip_ids))
for o in draft.filtered(lambda O: O.state != 'draft'):
    o.state = 'draft'
env.cr.commit()

# Recomputar trucking_trips para que funcionen bien los filtros.
sales._compute_trucking_trips()
env.cr.commit()


from datetime import datetime, timedelta
drivers = env['res.partner'].truck_drivers()
inactive = drivers.filtered(lambda d: not d.active_trucking_trip_id)
limit = timedelta(days=5)
def newer(d):
    if not d.trucking_trip_ids:
        return False
    return (datetime.now() - d.trucking_trip_ids[0].commitment_date) < limit

available = inactive.filtered(lambda i: newer(i))
# Sort desc
available =  available.sorted(lambda a: datetime.now() - a.trucking_trip_ids[0].commitment_date) 
for driver in available:
    driver.trucking_state='available'
env.cr.commit()

# Esto tarda:
drivers._compute_trucking_state_sequence(force=True)
env.cr.commit()

# Reactivar el cron de las CPE

# Y LITO

##############################

for o in sales:
     print(o,o.state,o.invoice_status,[t.state for t in o.trucking_trip_ids])
     
actives = env['sale.order'].search([('trucking_trip_active','=',True)])

env['res.partner'].search

tms in env['tms.order'].search([ ('is_cancelled','=',True)])


from datetime import datetime, timedelta
drivers = env['res.partner'].truck_drivers()
inactive = drivers.filtered(lambda d: not d.active_trucking_trip_id)
limit = timedelta(days=5)
def newer(d):
    if not d.trucking_trip_ids:
        return False
    return (datetime.now() - d.trucking_trip_ids[0].commitment_date) < limit

available = inactive.filtered(lambda i: newer(i))
# Sort desc
available =  available.sorted(lambda a: datetime.now() - a.trucking_trip_ids[0].commitment_date) 


[datetime.now() - x.trucking_trip_ids[0].commitment_date for x in inactive if x.trucking_trip_ids]
