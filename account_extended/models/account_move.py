from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    apply_tds = fields.Boolean(string="Apply TDS?")

    @api.onchange('partner_id')
    def onchange_vendor_id(self):
        for rec in self:
            rec.apply_tds = rec.partner_id.apply_tds
            if rec.partner_id.apply_tds:
                rec._onchange_apply_tds()

    @api.onchange('apply_tds')
    def _onchange_apply_tds(self):
        for rec in self:
            for line in rec.invoice_line_ids:
                if rec.apply_tds:
                    line.tax_ids = [(4, tds.id, False) for tds in rec.partner_id.tds_tax_id]
                else:
                    line.tax_ids = [(3, tds.id, False) for tds in rec.partner_id.tds_tax_id]

