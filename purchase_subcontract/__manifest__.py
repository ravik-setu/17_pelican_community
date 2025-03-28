# -*- coding: utf-8 -*-
{
    'name': "Purchase Subcontract",
    'summary': """To create subcontract based on the purchase order""",
    'description': """
       To create subcontract based on the purchase order
    """,
    'author': "Setu Consulting Services Pvt. Ltd.",
    'website': "https://www.setuconsulting.com",
    'category': 'manufacturing',
    'version': '16.1',
    'depends': ['purchase', 'mrp_subcontracting_dropshipping'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_view.xml',
        'views/purchase_order_view.xml',
        'views/subcontract_view.xml',
        'wizard/subcontract_specification_wizard_view.xml',
        'reports/subcontract_challan_template.xml',
        'views/subcontract_process_view.xml'
    ],
    'license': 'LGPL-3',

}
