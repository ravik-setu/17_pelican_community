from odoo import fields, models, api
from odoo.tools import OrderedSet, float_is_zero


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def update_reserved_quantity_based_on_location(self, move, need, assigned_moves_ids, partially_available_moves_ids,
                                                   lot_id=False):
        """
        Author: Ishani Manvar | Date: 25/03/25 | Task No: [1873] Odoo should Auto reserved selected lot in internal transfers
        Purpose: For updating reserved quantity in a move and quant.
        """
        available_quantity = move._get_available_quantity(move.location_id, lot_id=lot_id,
                                                          strict=False)
        if float_is_zero(available_quantity, precision_rounding=move.product_uom.rounding):
            return need
        taken_quantity = move.with_context(move_lines_not_to_update=True)._update_reserved_quantity(min(need, available_quantity),
                                                        available_quantity,
                                                        location_id=move.location_id,
                                                        lot_id=lot_id, strict=False)
        if float_is_zero(taken_quantity, precision_rounding=move.product_uom.rounding):
            return need
        need -= taken_quantity
        if float_is_zero(need - taken_quantity, precision_rounding=move.product_uom.rounding):
            assigned_moves_ids.add(move.id)
            return need
        partially_available_moves_ids.add(move.id)
        return need

    def set_reserve_based_on_lots(self, move_ids, lot_ids=[], force_qty=0):
        """
        Author: Ishani Manvar | Date: 25/03/25 | Task No: [1873] Odoo should Auto reserved selected lot in internal transfers
        Purpose: For updating reserved quantity in a move based on location.
        """
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        for move in move_ids:
            need = move.product_qty if not force_qty else force_qty
            if need:
                for lot_id in lot_ids:
                    need = self.update_reserved_quantity_based_on_location(move, need, assigned_moves_ids,
                                                                           partially_available_moves_ids,
                                                                           lot_id=lot_id)
                if not lot_ids:
                    need = self.update_reserved_quantity_based_on_location(move, need, assigned_moves_ids,
                                                                           partially_available_moves_ids)
        StockMove = self.env["stock.move"]
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})

    @api.model_create_multi
    def create(self, vals_list):
        """
        Author: Ishani Manvar | Date: 25/03/25 | Task No: [1873] Odoo should Auto reserved selected lot in internal transfers
        Purpose: For reserving the done quantity in a move line.
        """
        res = super(StockMoveLine, self).create(vals_list)
        lines_vals_list = []
        if res and not self.env.context.get('move_lines_not_to_update') and self.env.context.get('from_stock_move_operations'):
            for line in res:
                lines_vals_list.append({'location_id': line.location_id,
                                        'lot_id': line.lot_id,
                                        'qty_done': line.qty_done})
            move_id = res[0].move_id
            res.unlink()
            for line_dict in lines_vals_list:
                self.set_reserve_based_on_lots(move_id, line_dict.get('lot_id'), force_qty=line_dict.get('qty_done'))
            return self
        return res

    def write(self, vals):
        """
        Author: Ishani Manvar | Date: 25/03/25 | Task No: [1873] Odoo should Auto reserved selected lot in internal transfers
        Purpose: For reserving the updated done quantity in a move line.
        """
        if vals.get('qty_done') and self.env.context.get('from_stock_move_operations'):
            move_id = self.move_id
            move_line_id = move_id.move_line_ids.filtered(lambda ml:ml.reserved_uom_qty == self.qty_done)
            line_vals = {'location_id': move_line_id.location_id,
                         'lot_id': move_line_id.lot_id,
                         'qty_done': vals.get('qty_done')}
            move_line_id.unlink()
            self.set_reserve_based_on_lots(move_id, line_vals.get('lot_id'), force_qty=line_vals.get('qty_done'))
            return True
        res = super(StockMoveLine, self).write(vals)
        return res
