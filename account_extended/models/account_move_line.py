from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.move_id.apply_tds:
            self.tax_ids = [(4, tds.id, False) for tds in self.move_id.partner_id.tds_tax_id]