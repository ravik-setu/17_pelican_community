from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        """
        Author: Ishani Manvar | Date: 25/03/25 | Task No: [1873] Odoo should Auto reserved selected lot in internal transfers
        Purpose: For updating done quantity when move lines are created.
        """
        res = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        res.update({'qty_done': quantity})
        return res

    def _do_unreserve(self):
        """
        Author: Ishani Manvar | Date: 25/03/25 | Task No: [1873] Odoo should Auto reserved selected lot in internal transfers
        Purpose: For updating done quantity in moves.
        """
        res = super(StockMove, self)._do_unreserve()
        for rec in self:
            rec.move_line_ids.unlink()
            rec.write({'quantity_done': 0.0})
        return res

    def action_show_details(self):
        """
        Author: Ishani Manvar | Date: 26/03/25 | Task No: [1873] Odoo should Auto reserved selected lot in internal transfers
        Purpose: For updating context for custom methods.
        """
        res = super(StockMove, self).action_show_details()
        res.get('context').update({'from_stock_move_operations': True})
        return res
