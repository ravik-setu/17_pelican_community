# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'MRP Extended',
    'version': '16.0',
    'category': 'Product',
    'description': 'product_extended',
    'author': "Setu Consulting Services Pvt. Ltd.",
    'website': 'https://www.setuconsulting.com',
    'depends': ['production_planning', 'setu_wip_stock_valuation', 'setu_packaging', 'stock_extended'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_view.xml',
        'views/stock_quant_view.xml',
        'views/raw_material_stock_view.xml',
        'views/product_grade_view.xml',
        'views/mrp_production_planning_view.xml',
        'views/stock_picking_type_view.xml',
        'views/stock_lot_views.xml',
        'views/mrp_workorder_view.xml',
        'wizards/additional_product_wizard.xml',
        'wizards/user_restriction_warning_wizard.xml',
        'views/quality_check_view.xml',
        'views/stock_picking_views.xml',
    ],
    'demo': [
    ],
    'web': True,
    # 'installable': True,
    'application': True,
    'license': 'LGPL-3',
}