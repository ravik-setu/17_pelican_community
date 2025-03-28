from odoo import api, fields, models, tools, _


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if report_ref == 'mrp_extended.report_package_label_main':
            context = self.env.context.copy()
            context.update({'custom_paperformat': self.env.ref('mrp_extended.paperformat_package_label')})
            self.env.context = context
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
