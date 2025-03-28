from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_maintenance_request_type = fields.Selection(string='Auto Maintenance Request Type',
                                                     selection=[('dayswise', 'Days Wise'),
                                                                ('hourwise', 'Hour Wise')],
                                                     default='dayswise')
    is_required_breakdown_image = fields.Boolean(string='Required Breakdown Equipment Image')

    def set_values(self):
        """
        This method will set res config settings values.
        """
        res = super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set(model_name='res.config.settings', field_name='auto_maintenance_request_type',
                      value=self.auto_maintenance_request_type or 'dayswise', company_id=self.env.company.id)
        IrDefault.set(model_name='res.config.settings', field_name='is_required_breakdown_image',
                      value=self.is_required_breakdown_image or False, company_id=self.env.company.id)
        return res

    @api.model
    def get_values(self):
        """
        This method will get res config settings values.
        """
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        auto_maintenance_request_type = IrDefault._get(model_name='res.config.settings',
                                                      field_name='auto_maintenance_request_type',
                                                      company_id=self.env.company.id)
        is_required_breakdown_image = IrDefault._get(model_name='res.config.settings',
                                                    field_name='is_required_breakdown_image',
                                                    company_id=self.env.company.id)
        res.update({'auto_maintenance_request_type': auto_maintenance_request_type,
                    'is_required_breakdown_image': is_required_breakdown_image})
        return res
