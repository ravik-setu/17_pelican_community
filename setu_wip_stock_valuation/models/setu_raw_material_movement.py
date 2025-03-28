from odoo import fields, models, api


class SetuRawMaterialMovement(models.Model):
    _name = 'setu.raw.material.movement'
    _description = 'Raw Material Movement'

    production_id = fields.Many2one("mrp.production")
    product_id = fields.Many2one("product.product")
    quantity = fields.Float()
    location_id = fields.Many2one("stock.location")
    location_dest_id = fields.Many2one("stock.location")
