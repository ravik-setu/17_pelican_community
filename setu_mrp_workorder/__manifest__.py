# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Setu MRP II',
    'version': '17.0',
    'category': 'Manufacturing/Manufacturing',
    'sequence': 51,
    'summary': """Work Orders, Planning, Stock Reports.""",
    'depends': ['setu_quality', 'mrp', 'barcodes', 'setu_web_gantt', 'web_tour', 'hr_hourly_cost'],
    'auto_install': ['mrp'],
    'description': """Enterprise extension for MRP
* Work order planning.  Check planning by Gantt views grouped by production order / work center
* Traceability report
* Cost Structure report (mrp_account)""",
    'data': [
        'security/ir.model.access.csv',
        'security/mrp_workorder_security.xml',
        'data/mrp_workorder_data.xml',
        'views/hr_employee_views.xml',
        'views/quality_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_workorder_views.xml',
        'views/mrp_operation_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/stock_picking_type_views.xml',
        'views/res_config_settings_view.xml',
        'views/mrp_workorder_views_menus.xml',
        'wizard/additional_product_views.xml',
        'wizard/additional_workorder_views.xml',
        'wizard/propose_change_views.xml',
    ],
    'demo': [
        'data/mrp_production_demo.xml',
        'data/mrp_workorder_demo.xml',
        'data/mrp_workorder_demo_stool.xml'
    ],
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'setu_mrp_workorder/static/src/**/*.scss',
            'setu_mrp_workorder/static/src/**/*.js',
            'setu_mrp_workorder/static/src/**/*.xml',
        ],
        'web.assets_tests': [
            'setu_mrp_workorder/static/tests/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'setu_mrp_workorder/static/tests/**/*',
            ('remove', 'setu_mrp_workorder/static/tests/tours/**/*'),
        ],
    }
}
