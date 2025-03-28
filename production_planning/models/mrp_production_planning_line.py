# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpProductionPlanning(models.Model):
    _name = 'mrp.production.planning.line'
    _description = "Production Planning Lines"

    planning_id = fields.Many2one("mrp.production.planning", "Planning")
    product_id = fields.Many2one('product.product', 'Product')
    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine")
    qty = fields.Float('Qty')
    available_qty = fields.Float("Available in KG")
    available_qty_in_pcs = fields.Float("Available in PCS")
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company)
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        domain="""[
            '|',
                ('product_id', '=', product_id),
                '&',
                    ('product_tmpl_id.product_variant_ids', '=', product_id),
                    ('product_id','=',False),
            ('type', '=', 'normal'),
            '|',
                ('company_id', '=', company_id),
                ('company_id', '=', False)
            ]""",
        check_company=True)
    mo_count = fields.Integer("Manufacturing Orders", compute='_compute_mo_count')
    done_qty = fields.Float(string="Quantity", compute='_compute_mo_count')

    @api.depends('planning_id.mo_ids')
    def _compute_mo_count(self):
        for rec in self:
            product_mos = rec.find_product_mos()
            rec.mo_count = len(product_mos)
            rec.done_qty = sum(product_mos.mapped('qty_produced'))

    def open_manufacturing_orders(self):
        action = self.env.ref('mrp.mrp_production_action').sudo().read()[0]
        action['domain'] = [('id', 'in', self.find_product_mos().ids)]
        return action

    def find_product_mos(self):
        return self.planning_id.mo_ids.filtered(lambda mo: mo.product_id.id == self.product_id.id)
