from odoo import fields, models, api, _


class QualityCheck(models.Model):
    _inherit = "quality.check"

    def action_do_measure(self):
        """
        Author: Gaurav Vipani | Date: 05th Feb, 2024
        Purpose: This action will be used for popup measure wizard.
        """
        context = self.env.context.copy()
        context.update({'default_current_check_id': self.id,
                        'default_check_ids': self.ids})
        return {
            'name': _('Quality Check Failed'),
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('setu_quality_control.view_quality_check_wizard').id,
            'view_mode': 'form',
            'res_model': 'quality.check.wizard',
            'target': 'new',
            'context': context,
        }