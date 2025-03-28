from odoo import fields, models, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_subcontract = fields.Boolean(string="Is Subcontract?", related="order_id.is_subcontract")

    def add_specification(self):
        action = self.env.ref('purchase_subcontract.subcontract_specification_wizard_action').sudo().read()
        wiz_data = self.env['subcontract.specification.wizard'].create({'purchase_line_id': self.id})
        action[0]['res_id'] = wiz_data.id
        return action[0]
