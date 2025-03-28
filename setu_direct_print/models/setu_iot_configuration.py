from odoo import fields, models, api


class SetuIotConfiguration(models.Model):
    _name = 'setu.iot.configuration'
    _description = 'IOT Configuration'
    _rec_name = "server"

    server_user = fields.Char(string="User")
    server_pass = fields.Char(string="Password")
    server = fields.Char(string="Server")
    server_port = fields.Char(string="Port")
    report_ids = fields.Many2many('ir.actions.report', 'setu_iot_configuration_report_rel', 'configuration_id',
                                  'report_id',
                                  'Reports')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.company)

