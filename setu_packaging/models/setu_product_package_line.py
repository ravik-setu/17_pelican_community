from odoo import fields, models, api
import base64

class SetuProductPackageLine(models.Model):
    _name = 'setu.product.package.line'
    _description = 'Product Package Line'
    _order = 'id desc'

    package_id = fields.Many2one("setu.product.package")
    weight = fields.Float(digits=(4, 4))
    lot_id = fields.Many2one("stock.lot")
    quant_package_id = fields.Many2one("stock.quant.package")

    def action_generate_label(self, record, outer_package=False, setu_package_id=False):
        if not outer_package:
            content, content_type = self.env.ref('setu_packaging.action_package_label')._render_qweb_pdf(
                'setu_packaging.report_package_label_main', res_ids=[record.id])
        else:
            content, content_type = self.env.ref('setu_packaging.action_outer_package_label')._render_qweb_pdf(
                'setu_packaging.outer_package_report_label_main', res_ids=record.ids)

        name = "label {}".format(record.lot_id.name if not outer_package else  "outer " + ', '.join(record.quant_package_id.mapped('name')),)
        attachment_id = self.env['ir.attachment'].create({
            'name': name + ".pdf",
            'datas': base64.b64encode(content),
            'res_id': record.id if not outer_package else setu_package_id.id,
            'type': 'binary',
            'mimetype': 'application/pdf'
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'close_weight_wizard',
            'params': {
                'url': '/web/content/%s?download=1' % attachment_id.id,
            }
        }




