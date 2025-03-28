from odoo import fields, models, api
from odoo.tools.float_utils import float_round


class MrpProductionWorkcenterLine(models.Model):
    _inherit = 'mrp.workorder'

    total_component_available_qty = fields.Float(string='Total Available Quantity',
                                                 compute='_compute_total_component_available_qty')

    @api.depends("production_id", "move_raw_ids")
    def _compute_total_component_available_qty(self):
        """
        Author: Gaurav Vipani | Date: 28/08/2023
        Purpose: For shows available total component quantity.
        """
        for workorder in self:
            workorder.total_component_available_qty = sum(
                workorder.production_id.move_raw_ids.filtered(lambda move: move.state not in ['done', 'cancel']).mapped(
                    'reserved_availability'))

    def action_add_component(self):
        """
        Author: Gaurav Vipani | Date: 23/08/2023
        Purpose: For show only raw material product to add component wizard product_id.
        """
        res = super(MrpProductionWorkcenterLine, self).action_add_component()
        res.get('context').update(product_ids=self.production_id.move_raw_ids.mapped('product_id').ids)
        return res

    def action_generate_serial(self):
        super(MrpProductionWorkcenterLine, self).action_generate_serial()
        self.finished_lot_id.planning_lot_id = self.production_id.planning_lot_id.id

    def do_finish(self):
        """
        Author: Guarav Vipani | Date: 07th Nov, 2023
        Purpose: This method will be use for check user valid produce qty.
        """
        if not self.production_id.location_src_id.is_subcontracting_location:
            is_valid_producing_qty, action = self.production_id.is_valid_producing_qty()
            if not is_valid_producing_qty and action:
                return action
        return super(MrpProductionWorkcenterLine, self).do_finish()