from odoo import fields, models, api


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    planning_id = fields.Many2one('mrp.production.planning', related="production_id.planning_id")
