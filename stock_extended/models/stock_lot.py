from odoo import fields, models, api


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Author: Ishani Manvar | Date: 26/03/25 | Task No: [1873] Odoo should Auto reserved selected lot in internal transfers
        Purpose: For showing lots that have available quantity.
        """
        domain = args
        if self.env.context.get("find_available_lots", False) and domain:
            location_id = self.env.context.get("find_available_lots")
            if location_id:
                quant_ids = self.env["stock.quant"].search([('location_id', '=', location_id), ('available_quantity', '>', 0)])
                domain.append(('id', 'in', quant_ids.mapped("lot_id").ids))
        return super(StockLot, self)._name_search(name, domain, operator, limit, name_get_uid)
