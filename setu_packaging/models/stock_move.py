from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    product_package_id = fields.Many2one('setu.product.package')
