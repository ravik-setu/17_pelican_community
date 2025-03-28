# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Production Planning',
    'version': '16.0',
    'category': 'MRP',
    'description': 'Production Planning',
    'author': "Setu Consulting Services Pvt. Ltd.",
    'website': 'https://www.setuconsulting.com',
    'depends': ['mrp', 'purchase_subcontract', 'setu_packaging'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_production_planning_view.xml',
        'views/mrp_production_view.xml',
        'views/ir_sequence_view.xml',
        'views/mrp_workorder_view.xml',
        'views/res_partner_view.xml'
    ],
    'demo': [
    ],
    'web': True,
    # 'installable': True,
    'application': True,
    # 'auto_install': False,
    'license': 'LGPL-3',
}
