from odoo import fields, models, api


class StockPackageType(models.Model):
    _inherit = 'stock.package.type'

    package_product_id = fields.Many2one('product.product')
    product_config_line_ids = fields.One2many('package.type.product.config', 'package_type_id')
    prefix = fields.Char(string='Prefix', tracking=True)
