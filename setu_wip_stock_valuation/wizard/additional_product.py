from odoo import models, api, fields
from odoo.exceptions import UserError

class MrpWorkorderAdditionalProduct(models.TransientModel):
    _inherit = "mrp_workorder.additional.product"

    lot_id = fields.Many2one("stock.lot", string="Lot/Serial Number")
    is_return = fields.Boolean("Is Return?")

    def add_product(self):
        """
        Added By : Ravi Kotadiya | On : Aug-21-2023
        Use : To create internal transfer from RM to WIP and reserve product into related MO
        """
        production_id = self.workorder_id.production_id
        if not production_id.is_src_contain_wip_stock_location:
            self.env["stock.picking"].do_unreserve_and_reserve_from_lot(self.lot_id,
                                                                        move_ids=production_id.move_raw_ids,
                                                                        un_reserve=False, qty=self.product_qty)
            #return super(MrpWorkorderAdditionalProduct, self).add_product()
        production_id.create_internal_transfer(self.product_id, self.product_qty, self.lot_id)
        self.env["stock.picking"].do_unreserve_and_reserve_from_lot(self.lot_id,
                                                                    move_ids=production_id.move_raw_ids,
                                                                    un_reserve=False, qty=self.product_qty)
        production_id.create_raw_material_movement(self.product_id, self.product_qty,
                                                   production_id.location_src_id, production_id.location_dest_id)

    def return_product(self):
        """
        Added By : Ravi Kotadiya | On : Aug-21-2023
        Use : To create internal transfer from wip to Rm
        """
        production_id = self.workorder_id.production_id
        if not production_id.is_src_contain_wip_stock_location:
            return True
        production_reserved_qty = sum(production_id.move_raw_ids.mapped('quantity'))
        need_to_reserve = production_reserved_qty - self.product_qty
        if production_id.state not in ['done', 'cancel']:
            production_id.move_raw_ids._do_unreserve()
        max_return_qty = production_id.get_available_component_qty_for_return()
        if max_return_qty < self.product_qty:
            raise UserError("Sorry you can only move {}{} to raw material stock!".format(max_return_qty,
                                                                                        self.product_id.uom_id.name))
        production_id.create_internal_transfer(self.product_id, self.product_qty, self.lot_id, is_return=True)
        production_id.create_raw_material_movement(self.product_id, self.product_qty,
                                                   production_id.location_dest_id, production_id.location_src_id,
                                                   is_return=True)
        if need_to_reserve > 0:
            self.env["stock.picking"].do_unreserve_and_reserve_from_lot(self.lot_id, production_id.move_raw_ids,
                                                                        qty=need_to_reserve)
