from odoo import fields, models, api, _


class MaintenanceCheckpoint(models.Model):
    _name = 'maintenance.checkpoint'
    _description = 'Maintenance checkpoint'

    name = fields.Char()
    maintenance_checkpoint_template_id = fields.Many2one(
                                        comodel_name='maintenance.checkpoint.template',
                                        string='Check Points')
    preventive_maintenance_request_frequency = fields.Selection(
        string='Preventive Maintenance Request Frequency',
        selection=[('hourly', 'Hourly'),
                   ('daily', 'Daily'),
                   ('monthly', 'Monthly'),
                   ('quarterly', 'Quarterly'),
                   ('half_yearly', 'Half Yearly'),
                   ('yearly', 'Yearly')],
        related='maintenance_checkpoint_template_id.preventive_maintenance_request_frequency')
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company',
                                 related='maintenance_checkpoint_template_id.company_id')

    def name_get(self):
        """
        Author: Gaurav Vipani | Date: 26th July,2023
        Purpose: Added Name Pattern "name [ check point template ] - company"
        """
        result = []
        for check_point in self:
            if check_point.name and check_point.maintenance_checkpoint_template_id:
                name = _("{} [ {} ] - {}".format(check_point.name,
                                               check_point.maintenance_checkpoint_template_id,
                                               check_point.company_id))
                result.append((check_point.id, name))
            else:
                result.append((check_point.id, check_point.name))
        return result