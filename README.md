# Odoo Trucking


Odoo module for Trucking Companies.

Main features:

- Create trucks and trailers
- Mark res.partners as truck drivers. Relate drivers and trucks.
- Mantain a list of active/assigned/inactive drivers.
- Create products that represents trucking trips.
- When creating a sale order line with this products, a trucking.trip is created.
- Assign drivers to trips, via form or drag-and-drop them in the dashboard kanban.
- Support for Argentinian CPE (Carta de Porte Electronica) status tracking.
- Whatsapp integration: 
   - Request driver's confirmation via whatsapp utility template with quickreply buttons and process their response.
   - Notify customers of a trip assignment, including driver and vehicle data.
- Wizard to create sale orders with several trucks in one go.
- Support for pricelists that uses the trip distance as a factor instead of product_uom_qty
- Create customer invoices and drivers purchase orders using trip information.

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).