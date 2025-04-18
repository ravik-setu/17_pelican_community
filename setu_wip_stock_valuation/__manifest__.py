# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'WIP Stock Valuation',
    'version': '16.0',
    'category': 'account',
    'summary': """Valuation For WIP Stock""",
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',
    'description': """
    """,
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'license': 'OPL-1',
    'sequence': 20,
    'depends': ['stock_account', 'setu_mrp_workorder'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_location_view.xml',
        'wizard/additional_product_view.xml',
        'views/mrp_production_view.xml'
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'setu_wip_stock_valuation/static/src/**/*.xml',
    #     ],
    # },
    'application': True,
}
