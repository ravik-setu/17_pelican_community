from odoo import fields, models, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        """
        Added By : Ravi Kotadiya | On : Apr-18-2023 | Task : 2076
        Use : To move subcontract product in product default location
        """
        res = super(PurchaseOrderLine, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if picking.picking_type_id.code == 'incoming' and self.product_id.destination_location_id:
            res.update({'location_dest_id': self.product_id.destination_location_id.id})
        return res
