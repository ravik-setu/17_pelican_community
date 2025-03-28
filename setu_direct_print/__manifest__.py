{
    'name': 'Setu Direct Print',
    'version': '17.0.0.0',
    'category': 'Settings',
    'license': 'OPL-1',
    'description': """This module helps to Print PDF Directly Using configuration.""",
    'summary': 'This module helps to Print PDF Directly Using configuration.',

    # Author
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'maintainer': 'Setu Consulting Services Pvt. Ltd.',
    'website': 'https://www.setuconsulting.com/',
    'support': 'support@setuconsulting.com',

    # Dependencies
    'depends': ["base"],

    # Views
    'data': [
        'security/ir.model.access.csv',
        'views/setu_iot_configuration_view.xml',
        'views/res_users.xml'
    ],

    # Technical
    'installable': True,
    'auto_install': False,
    'application': True,
}
