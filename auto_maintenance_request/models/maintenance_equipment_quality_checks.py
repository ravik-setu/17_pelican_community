from odoo import fields, models, api


class MaintenanceEquipmentQualityChecks(models.Model):
    _name = 'maintenance.equipment.quality.checks'
    _description = 'Maintenance equipment quality checks'

    name = fields.Char(string="Name")
    maintenance_id = fields.Many2one("maintenance.request", string="Checklist")
    is_pass = fields.Boolean(string="Yes/No")
    is_not_applicable = fields.Boolean(string="Not Applicable")
    description_note = fields.Char(string="Remark")
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company',
                                 related='maintenance_id.company_id')

    @api.onchange('is_not_applicable', 'is_pass')
    def onchange_not_applicable(self):
        for rec in self:
            if rec.is_not_applicable:
                rec.is_pass = False
