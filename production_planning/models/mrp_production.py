from odoo import fields, models, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    planning_id = fields.Many2one('mrp.production.planning', copy=False)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine")
    planning_lot_id = fields.Many2one("planning.lot", related="planning_id.lot_id", string="Planning Lot", store=True)

    def write(self, vals):
        """
        Added By : Ravi Kotadiya | On : Apr-14-2023 | Task : 2114
        Use : To change machine into running workorders
        """
        res = super(MrpProduction, self).write(vals)
        if vals.get('workcenter_id'):
            for mo in self.filtered(lambda mo: mo.workorder_ids):
                Query = "update mrp_workorder set workcenter_id={} where {}".format(
                    mo.workcenter_id.id,
                    "id={}".format(mo.workorder_ids.id) if len(mo.workorder_ids) == 1 else "id in {}".format(
                        mo.workorder_ids._ids))
                self._cr.execute(Query)
        return res

    # def action_generate_serial(self):
    #     """
    #     Author: Gaurav Vipani | Date: 07th Feb, 2024
    #     Purpose: This method will be used for change lot name as per planning name.
    #     """
    #     self.ensure_one()
    #     res = super(MrpProduction, self).action_generate_serial()
    #     if self.planning_lot_id and self.lot_producing_id:
    #         self.lot_producing_id.name = self.planning_lot_id.name
    #     return res