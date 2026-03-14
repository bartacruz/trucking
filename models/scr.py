# Purchase






# MIGRATE FROM TMS
# Agregar los repos
# /opt/odoo-17/repos/sale-workflow,/opt/odoo-17/repos/purchase-workflow,/opt/odoo-17/repos/account-financial-tools
#
# Parar el cron de CPE
# Instalar Trucking (Camiones)
# Instalar tree remember tree column
# Cambiar el web responsive por el de OCA
# Ajustes -> Ventas -> Descuentos

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

#
# Porque el tms.sale usa el tms.factor indiscriminada y criminalmente...
# Solo por estas cosas creo que debe haber pena capital.
#
lines = env['sale.order.line'].search([])
for l in lines:
    l.tms_factor = 1

trucking_lines = lines.filtered(lambda L:
    L.trucking_trip_id and
    not L.order_id.pricelist_id and
    L.price_unit == 1
)
for l in trucking_lines:
    l.price_unit = l.product_id.list_price

env.cr.commit()

# Reimportar las listas de precios.
#
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


drivers = env['res.partner'].search([]).filtered(lambda d: d.truck_driver)
drivers.filtered(lambda d: d.tms_driver_id and d.vehicle_id != d.tms_driver_id.vehicle_id)
vehicles = env['fleet.vehicle'].search([]).filtered(lambda v: v.tms_driver_id and not v.driver_id)


for partner in env['res.partner'].search([]).filtered(lambda L: L.l10n_latam_identification_type_id.id == 1):
...     try:
...         partner.l10n_latam_identification_type_id = 4
...         env.cr.commit()
...     except:
...         print("ERR",partner)
