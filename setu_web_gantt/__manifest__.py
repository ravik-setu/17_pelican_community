# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SEtu Web Gantt',
    'category': 'Hidden',
    'description': """
Odoo Web Gantt chart view.
=============================

    """,
    'version': '17.0',
    'depends': ['web'],
    'assets': {
        'web._assets_primary_variables': [
            'setu_web_gantt/static/src/gantt_view.variables.scss',
        ],
        'web.assets_backend': [
            'setu_web_gantt/static/src/**/*',

            # Don't include dark mode files in light mode
            ('remove', 'setu_web_gantt/static/src/**/*.dark.scss'),
        ],
        'web.qunit_suite_tests': [
            'setu_web_gantt/static/tests/**/*',
            ('remove', 'setu_web_gantt/static/tests/**/*_mobile_tests.js'),
        ],
        'web.qunit_mobile_suite_tests': [
            'setu_web_gantt/static/tests/helpers.js',
            'setu_web_gantt/static/tests/**/*_mobile_tests.js',
        ],
        # ========= Dark Mode =========
        "web.dark_mode_variables": [
            ('before', 'web_enterprise/static/src/**/*.variables.scss', 'setu_web_gantt/static/src/**/*.variables.dark.scss'),
        ],
        "web.assets_web_dark": [
            'setu_web_gantt/static/src/**/*.dark.scss',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
