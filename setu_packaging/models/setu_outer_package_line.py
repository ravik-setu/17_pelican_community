from odoo import fields, models, api


class SetuOuterPackageLine(models.Model):
    _name = 'setu.outer.package.line'
    _description = 'Setu Outer Package Details'

    package_id = fields.Many2one("setu.product.package")
    product_id = fields.Many2one(string='Product', related='package_id.product_id')
    lot_id = fields.Many2one("stock.lot")
    quant_package_id = fields.Many2one("stock.quant.package")
    inner_package_line_id = fields.Many2one('setu.product.package.line')
    weight = fields.Float(digits=(4, 4))



