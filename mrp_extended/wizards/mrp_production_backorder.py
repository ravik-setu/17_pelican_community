from odoo import fields, models, api

class MrpProductionBackorder(models.TransientModel):

    _inherit = 'mrp.production.backorder'

    def action_backorder(self):
        """
        Author: Gaurav Vipani | Date: 8th Feb, 2023
        Purpose: This method will used for remain reserve qty move to
        """
        production_move_list = []
        production_id = self.mrp_production_backorder_line_ids.filtered(lambda l: l.to_backorder).mrp_production_id
        for move_raw_id in production_id.move_raw_ids:
            remain_qty = move_raw_id.reserved_availability - move_raw_id.quantity_done
        production_move_list.append({'product_id': move_raw_id.product_id.id,
                                     'lot_ids': move_raw_id.move_line_ids.mapped("lot_id"),
                                     'qty': remain_qty})
        res = super(MrpProductionBackorder, self).action_backorder()
        backorder_id = production_id.procurement_group_id.mrp_production_ids.filtered(lambda mo: mo.state == 'confirmed')
        picking_env = self.env["stock.picking"]
        backorder_id.move_raw_ids._do_unreserve()
        for production_move in production_move_list:
            if production_move.get('qty'):
                picking_env.do_unreserve_and_reserve_from_lot(lot_ids=production_move.get('lot_ids'),
                                                              move_ids=backorder_id.move_raw_ids,
                                                              qty=production_move.get('qty'))
        return res