from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    @api.onchange('location_dest_id', 'move_finished_ids', 'bom_id')
    def _onchange_location_dest(self):
        destination_location = self.location_dest_id
        update_value_list = []
        for move in self.move_finished_ids:
            update_value_list += [(1, move.id, ({
                'warehouse_id': destination_location.warehouse_id.id,
                'location_dest_id': destination_location.id,
            }))]
        self.move_finished_ids = update_value_list

    @api.onchange('location_src_id', 'move_raw_ids', 'bom_id')
    def _onchange_location(self):
        source_location = self.location_src_id
        self.move_raw_ids.update({
            'warehouse_id': source_location.warehouse_id.id,
            'location_id': source_location.id,
        })

    @api.model
    def create(self, vals):
        if vals.get('product_id') and not self.env.context.get('is_subcontract'):
            product = self.env["product.product"].browse(vals.get('product_id'))
            if product.destination_location_id:
                vals.update({'location_dest_id': product.destination_location_id.id})
            if product.source_location_id:
                vals.update({'location_src_id': product.source_location_id.id})
        res = super(MrpProduction, self).create(vals)
        # is_subcontract - used only for normal order so checked in our condition
        # skip_confirm - backorder not consuming material so checked in our condition
        if not self.env.context.get('is_subcontract') and not self.env.context.get('skip_confirm'):
            if product.destination_location_id:
                res._onchange_location_dest()
            if product.source_location_id:
                res._onchange_location()
        if res.procurement_group_id.mrp_production_ids:
            production_ids = res.procurement_group_id.mrp_production_ids
            planning_id = production_ids.mapped('planning_id')
            if planning_id:
                res.planning_id = planning_id[0].id
            if res.picking_type_id.use_parent_mo_lot and production_ids:
                res.write({'lot_producing_id': production_ids[0].lot_producing_id.id})
        return res

    def action_generate_serial(self):
        self.ensure_one()
        res = super(MrpProduction, self).action_generate_serial()
        self.lot_producing_id.planning_lot_id = self.planning_lot_id.id
        return res

    def _pre_button_mark_done(self):
        """
        Author: Gaurav Vipani | Date: 25/08/2023
        Purpose: For apply user restriction not to consume more product quantity then reserve.
        # Remove  not self.env.context.get('avoid_reserved_qty_check') if you want to check required qty is available or not in location
        """
        # if production not subcontracting type
        for production in self:
            if not production.location_src_id.is_subcontracting_location and not self.env.context.get('avoid_reserved_qty_check'):
                is_valid_producing_qty, action = production.is_valid_producing_qty()
                if not is_valid_producing_qty and action:
                    return action
        return super(MrpProduction, self)._pre_button_mark_done()

    def is_valid_producing_qty(self):
        """
        Author: Gaurav Vipani | Date: 07th Oct, 2023
        Purpose: This method will be use for check user produce qty is valid or not
        """
        self.ensure_one()
        action = {}
        for move in self.move_raw_ids.filtered(lambda move: move.state not in ['done', 'cancel']):
            round_precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            should_reserve = move.product_uom_qty * self.qty_producing / self.product_qty
            if should_reserve > move.reserved_availability:
                action = self.env["ir.actions.act_window"]._for_xml_id(
                    "mrp_extended.user_restriction_warning_action")
                action['context'] = {
                    'default_warning_msg': '<h4>You are trying {} product to consume more quantity then reserved. <br/>'
                                           'Reserved Qty : {} & Consume Qty : {} </h4>'.format(
                        move.product_id.name, move.reserved_availability,
                        float_round(should_reserve, precision_digits=round_precision, rounding_method='HALF-UP'))}
                return False, action
        return True, action

    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        super(MrpProduction, self)._cal_price(consumed_moves)
        finished_move = self.move_finished_ids.filtered(
            lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        if finished_move:
            finished_move.ensure_one()
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                finished_move.production_cost_details = "{} + {}".format(finished_move.price_unit,
                                                                         finished_move.product_id.production_cost)
                finished_move.price_unit = finished_move.price_unit + finished_move.product_id.production_cost
        return True