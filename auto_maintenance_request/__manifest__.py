{
    'name': 'Setu Auto Maintenance Request',
    'version': '17.0',
    'summary': 'Auto Maintenance Request',
    'author': 'SETU Consulting Services Pvt. Ltd.',
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',
    'category': 'maintenance',
    'depends': ['maintenance', 'hr_holidays'],
    'data': [
                'security/ir.model.access.csv',
                'data/ir_cron_data.xml',
                'views/maintenance_equipment_view.xml',
                'views/maintenance_checkpoint_template_views.xml',
                'views/maintenance_checkpoint_views.xml',
                'views/maintenance_equipment_quality_checks.xml',
                'views/maintenance_request.xml',
                'views/res_config_settings.xml',
            ],
    'installable': True,
    'auto_install': True
}