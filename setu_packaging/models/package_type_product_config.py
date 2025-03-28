from odoo import fields, models, api


class PackageTypeProductConfig(models.Model):
    _name = 'package.type.product.config'
    _description = 'Product configurations for a package type'

    product_id = fields.Many2one('product.product')
    package_type_id = fields.Many2one('stock.package.type')
    box_quantity = fields.Float(string='Box Quantity')
