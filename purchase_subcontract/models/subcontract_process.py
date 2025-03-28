from odoo import fields, models, api
from odoo.exceptions import UserError


class SubcontractProcess(models.Model):
    _name = 'subcontract.process'
    _description = 'Subcontract Process'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")

    @api.constrains('code')
    def _check_python_code(self):
        for rec in self:
            exist_rec = self.search([('code', '=ilike', rec.code), ('id', '!=', rec.id)])
            if exist_rec:
                raise UserError("Code already exist!")
