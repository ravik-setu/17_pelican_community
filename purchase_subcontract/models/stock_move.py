from odoo import fields, models, _, api


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self.env.context.get("picking_id", ''):
                vals['picking_id'] = self.env.context.get("picking_id")
        return super(StockMove, self).create(vals_list)
