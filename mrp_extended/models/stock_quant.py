# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import math


class StockQuant(models.Model):
    _inherit = "stock.quant"

    qty_in_pcs = fields.Boolean(string="Quantity in PCS")
    quant_qty = fields.Float(string="Qty In PCS", compute='_compute_quantity_in_pcs', store=True)
    planning_lot_id = fields.Many2one('planning.lot', related="lot_id.planning_lot_id", store=True)

    @api.depends('quantity')
    def _compute_quantity_in_pcs(self):
        for rec in self:
            if rec.product_id.show_qty_in_pcs and rec.location_id.usage == 'internal' and rec.product_id.weight:
                rec.quant_qty = math.ceil(rec.quantity / rec.product_id.weight)
