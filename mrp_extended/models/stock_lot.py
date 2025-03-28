# -*- coding: utf-8 -*-
from odoo import fields, models, _, api


class StockLot(models.Model):
    _inherit = "stock.lot"

    planning_lot_id = fields.Many2one('planning.lot', string="Planning Lot")

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Author: Gaurav Vipani | Date: 01st Nov, 2023
        Purpose: This method will be use for show only reserve lot in manufacturing order.
        """
        domain = args
        if self.env.context.get("is_need_to_find_available_stock_lot", False) and domain:

            production_id = self.env.context.get("production_id")
            if production_id:
                production_id = self.env["mrp.production"].browse(production_id)
                lot_ids = production_id.move_raw_ids.filtered(
                    lambda move: move.state not in ["done", "cancel"]).move_line_ids.mapped("lot_id")
                domain.append(('id', 'in', lot_ids.ids))

            if not production_id:
                quant_ids = self.env["stock.quant"].search(domain)
                quant_ids = quant_ids.filtered(
                    lambda quant: quant.location_id.usage == 'internal' and quant.available_quantity > 0)
                domain.append(('id', 'in', quant_ids.mapped("lot_id").ids))

        if self.env.context.get('add_comp_product'):
            product_id = self.env['product.product'].browse(self.env.context.get('add_comp_product'))
            if product_id.is_raw_material:
                dest_loc = product_id.destination_location_id
                quant_ids = self.env["stock.quant"].search([('location_id', '=', dest_loc.id), ('available_quantity', '>', 0)])
                domain.append(('id', 'in', quant_ids.mapped("lot_id").ids))
            else:
                if self.env.context.get('wo_add_comp'):
                    src_loc = self.env['mrp.workorder'].browse(self.env.context.get('wo_add_comp')).production_id.location_src_id
                    quant_ids = self.env["stock.quant"].search([('location_id', '=', src_loc.id), ('available_quantity', '>', 0)])
                    domain.append(('id', 'in', quant_ids.mapped("lot_id").ids))
        return super(StockLot, self)._name_search(name, domain, operator, limit, name_get_uid)
