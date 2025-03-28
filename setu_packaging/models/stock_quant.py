from odoo import fields, models, api
from odoo.osv import expression

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        domain = super(StockQuant, self)._get_gather_domain(product_id, location_id, lot_id=lot_id,
                                                            package_id=package_id, owner_id=owner_id, strict=strict)
        if self.env.context.get('apply_package_domain'):
            domain = expression.AND([[('package_id', '=', False)], domain])
        return domain
