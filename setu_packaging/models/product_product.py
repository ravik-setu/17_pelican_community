from odoo import fields, models, api
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    put_in_pack = fields.Boolean(string="Put In Pack", related='product_tmpl_id.put_in_pack', readonly=False, store=True)
    put_in_pack_product_id = fields.Many2one("product.product", string="Put in Pack Product",
                                             related='product_tmpl_id.put_in_pack_product_id', readonly=False, store=True)
    qty_in_pack = fields.Float(string="Quantity", related='product_tmpl_id.qty_in_pack', readonly=False, store=True)

    @api.constrains('put_in_pack')
    def _check_qty_in_pack(self):
        for rec in self:
            if rec.put_in_pack and not rec.qty_in_pack:
                raise UserError("Number of unit in pack must be set")