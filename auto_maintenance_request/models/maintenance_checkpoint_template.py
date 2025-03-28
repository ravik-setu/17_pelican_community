from odoo import fields, models, api, _
from odoo.exceptions import UserError

class MaintenanceCheckpointTemplate(models.Model):

    _name = 'maintenance.checkpoint.template'
    _description = 'Maintenance checkpoint template'

    name = fields.Char(required=True)
    preventive_maintenance_request_frequency = fields.Selection(
        string='Preventive Maintenance Request Frequency',
        selection=[('hourly', 'Hourly'),
                   ('daily', 'Daily'),
                   ('monthly', 'Monthly'),
                   ('quarterly', 'Quarterly'),
                   ('half_yearly', 'Half Yearly'),
                   ('yearly', 'Yearly')],
        required=True)
    maintenance_check_point_ids = fields.One2many(comodel_name='maintenance.checkpoint',
                                                  inverse_name='maintenance_checkpoint_template_id',
                                                  string='Check Points')
    maintenance_equipment_ids = fields.Many2many(comodel_name='maintenance.equipment',
                                                 string='Equipments',
                                                 domain="[('company_id', '=', company_id)]")
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company',
                                 required=True,
                                 default=lambda self: self.env.company)

    @api.constrains('preventive_maintenance_request_frequency', 'maintenance_equipment_ids')
    def _constrains_maintenance_equipment_ids(self):
        """
        Author: Gaurav Vipani | Date: 26th July,2023
        Purpose: For unique equipment for each checklist
        """
        for rec in self:
            if rec.maintenance_equipment_ids:
                for maintenance_equipment_id in rec.maintenance_equipment_ids.ids:
                    is_checklist_exist = self.search([
                        ('id', '!=', rec.id), ('company_id', '=', rec.company_id.id),
                        ("preventive_maintenance_request_frequency", '=',
                         rec.preventive_maintenance_request_frequency),
                        ('maintenance_equipment_ids', 'in', [maintenance_equipment_id])
                    ])
                    if is_checklist_exist:
                        error_message = _("Checklist already exist with Maintenance " \
                                         "frequency {}".format(
                            dict(self._fields[
                                     'preventive_maintenance_request_frequency'].selection).get(
                                rec.preventive_maintenance_request_frequency)))
                        raise UserError(error_message)

    def name_get(self):
        """
        Author: Gaurav Vipani | Date: 26th July,2023
        Purpose: Added Name Pattern "name [ frequency ] - company"
        """
        result = []
        for checkpoint_template in self:
            if checkpoint_template.name and checkpoint_template.preventive_maintenance_request_frequency:
                name = _("{} [ {} ] - {}".format(checkpoint_template.name,
                (dict(self._fields['preventive_maintenance_request_frequency'].selection)
                .get(checkpoint_template.preventive_maintenance_request_frequency)),
                checkpoint_template.company_id.name))
                print(name)
                result.append((checkpoint_template.id, name))
            else:
                result.append((checkpoint_template.id, checkpoint_template.name))
        return result