# -*- coding: utf-8 -*-
{
    'name': "Trucking",

    'summary': "Trucking company support",

    'description': """
        Trucking company support for Odoo.
    """,

    'author': "Julio Santa Cruz",
    'website': "https://www.bartatech.com",
    'category': 'TMS',
    "version": "17.0.1.0.2",
    "license": "AGPL-3",

    'depends': ['base','fleet', 'sale','l10n_ar_afip_cpe','mail_gateway_whatsapp'],
    "assets": {
        "web.assets_backend": [
            'trucking/static/src/components/trucking_trips.js',
            'trucking/static/src/components/trucking_trips.xml',
            
            
        #     "tms_shipment/static/src/js/driver_list.js",
        #     "tms_shipment/static/src/js/driver_list.scss",
        #     "tms_shipment/static/src/js/driver_list.xml",
        #     "tms_shipment/static/src/js/kanban_controller.js",
        #     "tms_shipment/static/src/js/kanban_controller.scss",
        #     "tms_shipment/static/src/js/kanban_controller.xml",
        #     "tms_shipment/static/src/js/tms_kanban.js",
        #     "tms_shipment/static/src/views/fields/many2many_trip_field.js",
        #     "tms_shipment/static/src/views/fields/many2many_trip_field.scss",
        #     "tms_shipment/static/src/views/fields/many2many_trip_field.xml",
        #     "tms_shipment/static/src/views/fields/tms_service.js",
        #     "tms_shipment/static/src/views/fields/trips_field.js",
        #     "tms_shipment/static/src/views/fields/trips_field.xml",
        #     "tms_shipment/static/src/js/dynamic_m2o_field.js",
        #     # "tms_shipment/static/src/xml/dynamic_m2o_field.xml",
            
        ],
    },
    'data': [
        'data/ir_sequence_data.xml',
        "security/ir.model.access.csv",
        'views/fleet_vehicle.xml',
        'views/product_template.xml',
        'views/res_partner.xml',
        'views/sale_order.xml',
        'views/trucking_trip.xml',
        'views/menu.xml',
    ],
    "maintainers": ["bartacruz"],
    "application": True,
}

