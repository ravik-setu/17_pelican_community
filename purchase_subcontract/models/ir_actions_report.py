from odoo import api, fields, models, tools, _


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if report_ref == 'purchase_subcontract.report_subcontract_challan':
            context = self.env.context.copy()
            context.update({'custom_paperformat': self.env.ref('purchase_subcontract.paperformat_challan')})
            self.env.context = context
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    @api.model
    def get_paperformat(self):
        if self.env.context.get('custom_paperformat'):
            paperformat_id = self.env.context.get('custom_paperformat')
            return paperformat_id
        return super(IrActionsReport, self).get_paperformat()
