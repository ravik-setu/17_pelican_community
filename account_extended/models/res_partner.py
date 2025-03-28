from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_tax_domain(self):
        return [('tax_group_id', 'in',
                 [self.env.ref('l10n_in_tcs_tds.tcs_group').id, self.env.ref('l10n_in_tcs_tds.tds_group').id])]

    apply_tds = fields.Boolean(string="Apply TDS?", default=False)
    tds_tax_id = fields.Many2one(comodel_name='account.tax')
