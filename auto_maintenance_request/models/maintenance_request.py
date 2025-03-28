from odoo import fields, models, api, _
from odoo.exceptions import UserError

class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    preventive_maintenance_frequency = fields.Selection(selection=[('hourly', 'Hourly'), ('daily', 'Daily'),
                                                                   ('weekly', 'Weekly'), ('monthly', 'Monthly'),
                                                                   ('quarterly', 'Quarterly'),
                                                                   ('half_yearly', 'Half Yearly'),
                                                                   ('yearly', 'Yearly')],
                                                        tracking=True)
    maintenance_equipment_quality_checks_ids = fields.One2many(
        comodel_name='maintenance.equipment.quality.checks',
        inverse_name='maintenance_id',
        string='Maintenance Equipment Quality Checks')
    maintenance_equipment_image = fields.Binary(string="Equipment Image")
    file_name = fields.Char(string='File Name')

    @api.model_create_multi
    def create(self, vals_list):
        maintenance_requests = super().create(vals_list)
        is_required_breakdown_image = self.env['ir.default'].sudo().get(model_name='res.config.settings',
                                                                        field_name='is_required_breakdown_image',
                                                                        company_id=self.env.company.id)
        for request in maintenance_requests:
            if request.maintenance_type == 'corrective' and is_required_breakdown_image and not request.maintenance_equipment_image:
                raise UserError(_("Please upload breakdown equipment image."))
        return maintenance_requests

    def write(self, vals):
        res = super(MaintenanceRequest, self).write(vals)
        is_required_breakdown_image = self.env['ir.default'].sudo().get(model_name='res.config.settings',
                                                                        field_name='is_required_breakdown_image',
                                                                        company_id=self.env.company.id)
        if self.maintenance_type == 'corrective' and is_required_breakdown_image and not self.maintenance_equipment_image:
            raise UserError(_("Please upload breakdown equipment image."))
        return res