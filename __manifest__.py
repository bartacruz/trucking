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
    "version": "17.0.2.0.2",
    "license": "AGPL-3",

    'depends': ['base','fleet', 'sale','l10n_ar_afip_cpe','mail','mail_gateway_whatsapp','tms_sale','tms_shipment'],
    "assets": {
        "web.assets_backend": [
            'trucking/static/src/components/*',
            'trucking/static/src/js/*',
        ],
    },
    'data': [
        'wizard/trucking_create_so.xml',
        'data/ir_sequence_data.xml',
        "security/ir.model.access.csv",
        'views/afip_cpe.xml',
        'views/fleet_vehicle.xml',
        'views/product_pricelist.xml',
        'views/product_template.xml',
        'views/res_partner.xml',
        'views/sale_order.xml',
        'views/trucking_trip.xml',
        'views/menu.xml',
        'views/report_invoice.xml'
    ],
    "maintainers": ["bartacruz"],
    "application": True,
}

