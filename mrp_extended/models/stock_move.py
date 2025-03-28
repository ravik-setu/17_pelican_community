from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = "stock.move"

    package_id = fields.Many2one("setu.product.package")
    production_cost_details = fields.Text(string="Production Cost Details")

    @api.model
    def create(self, vals):
        if self.env.context.get("package_id", ''):
            vals.update({'package_id': self.env.context.get("package_id")})
        return super(StockMove, self).create(vals)