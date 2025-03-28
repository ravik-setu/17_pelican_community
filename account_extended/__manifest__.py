{
    'name': "Setu Account Extended",
    'version': '17.0',
    'category': 'Account Extended',
    'description': 'Account Extended',
    'author': "Setu Consulting Services Pvt. Ltd.",
    'website': "https://www.setuconsulting.com",
    'depends': ['l10n_in_withholding', 'setu_account_reports'],
    'data': [
        'views/res_partner_view.xml',
        'views/account_move_view.xml',
        'wizards/account_report_wizard_view.xml',
    ],
    'license': 'LGPL-3',
    'application': True,
    'installable': True
}
