# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Setu Packaging',
    'version': '16.0',
    'category': 'Package',
    'summary': """Put Product into Pack""",
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',
    'description': """
    """,
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'license': 'OPL-1',
    'sequence': 20,
    'depends': ['stock', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'report/package_label_view.xml',
        'report/outer_package_label_view.xml',
        'views/product_product_view.xml',
        'views/product_template_view.xml',
        'views/setu_product_package_view.xml',
        'views/ir_sequence_view.xml',
        'views/stock_package_type_view.xml',
        'views/package_type_product_config_view.xml',
        'views/stock_quant_package_views.xml',
        'wizard/package_weight_wizard_view.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'setu_packaging/static/src/**/*.js',
        ],
    },
    'application': True,
}
