from odoo import fields, models, api
from odoo.osv import expression


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Author: Ishani Manvar | Date: 09/09/24 | Task No: 814 Create Outer Package
        Purpose: For showing different lots for inner and outer packages.
        """
        domain = args
        location = self.env["stock.location"]
        product_obj = self.env["product.product"]
        if self.env.context.get('lots_for_outer_package'):
            product_id = product_obj.search([('id', '=', self.env.context.get('lots_for_outer_package'))])
            if hasattr(product_obj, 'destination_location_id') and product_id.destination_location_id:
                location = product_id.destination_location_id
            else:
                user_company = self.env.company
                warehouse = self.env['stock.warehouse'].search(
                    [('company_id', '=', user_company.id)], limit=1
                )
                if warehouse:
                    location = warehouse.lot_stock_id
            lot_ids = self.env['stock.lot'].search([('product_id', '=', product_id.id)])
            quants = self.env['stock.quant'].search(
                [('lot_id', 'in', lot_ids.ids),
                 ('location_id', '=', location.id),
                 ('on_hand', '=', True),
                 ('package_id', '!=', None),
                 ('package_id.outer_package', '=', False)])
            domain = expression.AND([
                domain,
                [('id', 'in', quants.mapped('lot_id')._ids)]
            ])
        if self.env.context.get('product_id'):
            product_id = product_obj.browse(self.env.context.get('product_id'))
            if hasattr(product_obj, 'destination_location_id') and product_id.destination_location_id:
                location = product_id.destination_location_id
            else:
                user_company = self.env.company
                warehouse = self.env['stock.warehouse'].search(
                    [('company_id', '=', user_company.id)], limit=1
                )
                if warehouse:
                    location = warehouse.lot_stock_id
            quants = self.env["stock.quant"]._gather(product_id, location)
            # quants = quants.filtered(lambda quant: not quant.package_id.id and quant.available_quantity)
            quants = quants.filtered(lambda quant: quant.available_quantity)
            domain = expression.AND([
                domain,
                [('id', 'in', quants.mapped('lot_id')._ids)]
            ])
        return super(StockLot, self)._name_search(name, domain, operator, limit, name_get_uid)
