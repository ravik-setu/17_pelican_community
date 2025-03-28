from odoo import fields, models, api
from odoo.osv import expression


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    setu_package_id = fields.Many2one('setu.product.package')
    move_line_ids = fields.One2many('stock.move.line', 'outer_quant_package_id')
    contained_qty = fields.Integer(compute='_compute_contained_qty_weight', store=True, copy=False)
    net_weight = fields.Float(compute='_compute_contained_qty_weight', store=True, copy=False)
    total_weight = fields.Float(copy=False)
    weight_uom_name = fields.Char(copy=False)
    outer_package = fields.Boolean(copy=False)
    is_unpacked = fields.Boolean(copy=False)

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        product_obj = self.env["product.product"]
        if self.env.context.get('product_id'):
            product_id = product_obj.search([('id', '=', self.env.context.get('product_id'))])
            if hasattr(product_obj, 'destination_location_id') and product_id.destination_location_id:
                location = product_id.destination_location_id
            quants = self.env["stock.quant"].search(
                [('location_id', '=', location.id), ('product_id', '=', product_id.id),
                 ('package_id', '!=', False), ('quantity', '>', 0)])
            package_ids = quants.mapped('package_id')
            domain = expression.AND([
                domain,
                [('id', 'in', package_ids._ids)]
            ])
        return super()._name_search(name, domain, operator, limit, order)

    def update_name_based_on_package_type(self):
        """
        Author: Ishani Manvar | Date: 06/09/24 | Task No: 814 Create Outer Package
        Purpose: For creating a name based on the given prefix in package type.
        """
        sequence = self.env.ref('stock.seq_quant_package')
        if self.package_type_id.prefix:
            name = self.name.replace(sequence.prefix, '')
            self.name = self.package_type_id.prefix + name

    @api.depends('quant_ids.quantity')
    def _compute_contained_qty_weight(self):
        """
        Author: Ishani Manvar | Date: 09/09/24 | Task No: 814 Create Outer Package
        Purpose: For computing the contained qty and net weight of a quant package.
        """
        for rec in self:
            quant_ids = rec.quant_ids
            if quant_ids:
                if rec.setu_package_id and rec.setu_package_id.outer_box:
                    rec.contained_qty = sum(
                        rec.setu_package_id.outer_package_line_ids.mapped('quant_package_id').mapped('contained_qty'))
                    rec.net_weight = sum(
                        rec.setu_package_id.outer_package_line_ids.mapped('quant_package_id').mapped('net_weight'))
                    rec.total_weight = rec.setu_package_id.total_weight
                else:
                    net_weight = 0
                    total_weight = 0
                    rec.contained_qty = sum(quant_ids.mapped('quantity'))
                    product_ids = quant_ids.mapped('product_id')
                    for product_id in product_ids:
                        unit_weight = product_id.weight
                        quant = quant_ids.filtered(lambda x: x.product_id == product_id)
                        product_qty = sum(quant.mapped('quantity'))
                        total_product_weight = product_qty * unit_weight
                        net_weight += total_product_weight
                        total_weight += net_weight
                    rec.net_weight = net_weight

    def unpack_outer_package(self):
        """
        Author: Ishani Manvar | Date: 10/09/24 | Task No: 814 Create Outer Package
        Purpose: For unpacking an outer package into their respective inner packages.
        """
        if self.outer_package:
            setu_product_package = self.env['setu.product.package'].search([('package_ids', 'in', self.id)])
            move_lines = self.move_line_ids or self.setu_package_id.picking_id.move_line_ids
            move_lines_to_unpack = move_lines.filtered(lambda ml: ml.result_package_id == self)
            for ml in move_lines_to_unpack:
                lot_id = ml.lot_id
                package_id = ml.package_id
                quant = self.env['stock.quant'].create({
                    'product_id': setu_product_package.product_id.id,
                    'location_id': setu_product_package.package_ids.location_id.id,
                    'quantity': ml.qty_done,
                    'lot_id': lot_id.id,
                    'package_id': package_id.id
                })
            for quant in self.quant_ids:
                quant.write({'inventory_quantity': 0})
                quant.action_apply_inventory()
            self.write({'contained_qty': 0, 'net_weight': 0, 'total_weight': 0, 'weight_uom_name': '', 'is_unpacked': True})
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
