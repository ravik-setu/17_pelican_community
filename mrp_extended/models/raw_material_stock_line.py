from odoo import fields, models, api


class RawMaterialStockLine(models.Model):
    _name = 'raw.material.stock.line'
    _description = 'Raw Material Stock Line'

    parent_product_id = fields.Many2one("product.product", string="R.M Size")
    product_id = fields.Many2one("product.product", string="Actual Size")
    grade_id = fields.Many2one("product.grade", related="product_id.grade_id")
    total_qty = fields.Float(string="Total Qty")
    order_qty = fields.Float(string="Order Qty")
    stock_qty = fields.Float(string="Spare Qty")
    process = fields.Char(string="Wire Process")
    current_stage = fields.Char(string="Current Stage")
    uom_id = fields.Many2one("uom.uom", related="product_id.uom_id")
    raw_material_stock_id = fields.Many2one("raw.material.stock")
