from odoo import fields, models, api
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    type = fields.Selection(selection_add=[('packaging', 'Packaging')], ondelete={'packaging': 'set default'})

    @api.constrains('type')
    def _check_is_valid_type(self):
        for rec in self:
            if type == 'packaging' and rec.operation_ids:
                raise UserError("Please remove lines from operation tab!")

    @api.constrains('product_qty', 'type')
    def is_valid_packaging_bom(self):
        for rec in self:
            pack_qty = rec.product_id.qty_in_pack or rec.product_tmpl_id.product_variant_ids[0].qty_in_pack
            if rec.type == 'packaging' and pack_qty and rec.product_qty % pack_qty != 0:
                raise UserError("The quantity must be in multiple of {}".format(pack_qty))

    @api.model_create_multi
    def create(self, vals_list):
        res = super(MrpBom, self).create(vals_list)
        for rec in res:
            for line in rec.bom_line_ids:
                rec.mark_product_as_resupply_to_subcontractor(line)
        return res

    def write(self, vals):
        res = super(MrpBom, self).write(vals)
        for line in self.bom_line_ids:
            self.mark_product_as_resupply_to_subcontractor(line)
        return res

    def mark_product_as_resupply_to_subcontractor(self, line):
        if line.bom_id.type == 'subcontract':
            line.product_id.route_ids = [(4, line.env.ref("mrp_subcontracting.route_resupply_subcontractor_mto").id)]