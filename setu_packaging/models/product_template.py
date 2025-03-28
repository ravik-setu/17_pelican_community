from odoo import fields, models, api
from odoo.exceptions import UserError

class ProductTemplate(models.Model):

    _inherit = 'product.template'

    put_in_pack = fields.Boolean(string="Put In Pack")
    put_in_pack_product_id = fields.Many2one("product.product", string="Put in Pack Product")
    qty_in_pack = fields.Float(string="Quantity")

    @api.constrains('put_in_pack')
    def _check_qty_in_pack(self):
        for rec in self:
            if rec.put_in_pack and not rec.qty_in_pack:
                raise UserError("Number of unit in pack must be set")