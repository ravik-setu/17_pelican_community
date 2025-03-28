from odoo import fields, models, api
from odoo.tools.misc import clean_context, OrderedSet, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    production_order_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    production_qty = fields.Float(string="Production Qty")

    def do_unreserve_and_reserve_from_lot(self, lot_ids, move_ids=False, un_reserve=True, qty=0):
        move_ids = move_ids or self.move_ids
        if un_reserve:
            move_ids._do_unreserve()
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        for move in move_ids:
            need = qty or move.product_qty - sum(move.move_line_ids.mapped('reserved_qty'))
            for lot_id in lot_ids.filtered(lambda lot: lot.product_id.id == move.product_id.id):
                if not need:
                    continue
                available_quantity = move._get_available_quantity(move.location_id, lot_id=lot_id, strict=False)
                if float_round(available_quantity, precision_rounding=move.product_uom.rounding) < need:
                    raise UserError(
                        "You have only {}{} in {}".format(round(available_quantity, 4), move.product_id.uom_id.name,
                                                          move.location_id.display_name))
                if float_is_zero(available_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                taken_quantity = move._update_reserved_quantity(need, min(need, available_quantity), move.location_id,
                                                                lot_id, strict=False)
                if float_is_zero(taken_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                if float_is_zero(need - taken_quantity, precision_rounding=move.product_uom.rounding):
                    assigned_moves_ids.add(move.id)
                    break
                partially_available_moves_ids.add(move.id)
        StockMove = self.env["stock.move"]
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
