from odoo import fields, models, api


class PurchaseSubcontractLine(models.Model):
    _name = 'purchase.subcontract.line'
    _description = 'Purchase Subcontract Line'

    purchase_id = fields.Many2one("purchase.order", string="Purchase Order")
    product_id = fields.Many2one("product.product", string="Sub Contract Product")
    product_qty = fields.Float(string="Quantity")
    partner_id = fields.Many2one("res.partner", string="Vendor")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(PurchaseSubcontractLine, self).create(vals_list)
        for rec in res:
            if not rec.partner_id:
                rec.partner_id = rec.purchase_id.partner_id.id
        return res
