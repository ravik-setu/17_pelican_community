from odoo import fields, models, api, SUPERUSER_ID
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    subcontract_required = fields.Boolean(string="Go For Subcontract?", related='purchase_id.subcontract_required')
    is_subcontract = fields.Boolean(string="Is Subcontract?", related='purchase_id.is_subcontract', store=True)
    loss_qty = fields.Float(string="Loss Quantity", copy=False)
    source_picking_id = fields.Many2one("stock.picking", string="Receipt", related="purchase_id.source_picking_id")
    subcontract_created = fields.Boolean(string="Is Subcontract Created?")

    def action_view_subcontract(self):
        purchase_obj = self.env["purchase.order"]
        action = purchase_obj._get_action_view_purchase(
            purchase_obj.search([('source_picking_id', '=', self.id)]))
        return action

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        domain = args
        if self.env.context.get('find_available_purchase'):
            purchase_ids = self.env['purchase.order'].find_available_purchase_lot()
            purchase_ids = purchase_ids.filtered(lambda po: po.state != 'cancel')
            domain = expression.AND([
                domain,
                [('id', 'in', purchase_ids.mapped('picking_ids').filtered(
                    lambda pick: pick.picking_type_id.code == 'incoming' and not pick.subcontract_created)._ids)]
            ])
        return super()._name_search(name, domain, operator, limit, name_get_uid)

    def do_unreserv_and_reserve_based_on_picking(self):
        self.move_ids._do_unreserve()
        purchase = self.find_purchase_based_on_origin()
        lot_ids = purchase.source_picking_id.mapped('move_line_nosuggest_ids').mapped('lot_id')
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        for move in self.move_ids:
            need = move.product_qty - sum(move.move_line_ids.mapped('reserved_qty'))
            for lot_id in lot_ids.filtered(lambda lot: lot.product_id.id == move.product_id.id):
                if not need:
                    continue
                available_quantity = move._get_available_quantity(move.location_id, lot_id=lot_id, strict=False)
                if float_is_zero(available_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                taken_quantity = move._update_reserved_quantity(need, min(need, available_quantity), move.location_id,
                                                                lot_id, strict=False)
                if float_is_zero(taken_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                purchase.source_picking_id.write({'subcontract_created': True})
                if float_is_zero(need - taken_quantity, precision_rounding=move.product_uom.rounding):
                    assigned_moves_ids.add(move.id)
                    break
                partially_available_moves_ids.add(move.id)
        StockMove = self.env["stock.move"]
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})

    def action_assign(self):
        res = super(StockPicking, self).action_assign()
        for picking in self:
            if picking.is_subcontract:
                purchase = self.find_purchase_based_on_origin()
                if purchase and purchase.source_picking_id:
                    self.do_unreserv_and_reserve_based_on_picking()
        return res

    def find_purchase_based_on_origin(self):
        picking_id = self.env["stock.picking"].search([('name', '=ilike', self.origin)])
        return picking_id.purchase_id

    def create_quant_and_do_inventory_adjustment_for_subcontract(self, product_id, qty, location_id, lot_id):
        quant_obj = self.env['stock.quant']
        if not self.env.context.get('package_id'):
            quant_obj = self.env['stock.quant'].with_context(picking_id=self.id)
        quant = quant_obj.create({
            'product_id': product_id.id,
            'inventory_quantity': qty,
            'location_id': location_id.id,
            'lot_id': lot_id.id
        })
        quant.with_user(SUPERUSER_ID).action_apply_inventory() if not self.user_has_groups(
            'stock.group_stock_manager') else quant.action_apply_inventory()
        # unprocessed_move._compute_should_consume_qty()
        quant._quant_tasks()
        return quant

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if (self.env.context.get('skip_backorder') or self.env.context.get(
                    'skip_immediate')) and picking.is_subcontract:
                dest_location = self.move_ids.location_id
                pickings = self.purchase_id._get_subcontracting_resupplies()
                pickings = pickings.filtered(lambda pick: pick.state == 'done')
                product_ids = pickings.mapped('move_ids').mapped('product_id')
                is_loss_qty_available = True if self.loss_qty else False
                loss_qty = self.loss_qty or self.get_total_loss_qty(product_ids)
                for product in product_ids:
                    for lot_id in pickings.mapped('move_line_nosuggest_ids').mapped('lot_id'):
                        if not loss_qty:
                            continue
                        qunts = self.search_quant_based_on_product_lot_and_location(product, dest_location,
                                                                                    lot_id)
                        available_quantity = sum(qunts.mapped('quantity'))
                        if not available_quantity:
                            continue
                        use_qty = min(loss_qty, available_quantity)
                        self.create_quant_and_do_inventory_adjustment_for_subcontract(product, -use_qty,
                                                                                      dest_location,
                                                                                      lot_id)
                        _logger.info("Loss Qty: Picking: {}, Location: {}, Serial: {},Qty: {}".format(picking.id,
                                                                                                      dest_location.name,
                                                                                                      lot_id.name,
                                                                                                      use_qty))
                        if not is_loss_qty_available:
                            loss_qty -= use_qty
                        if not  self.loss_qty:
                            self.write({"loss_qty": self.loss_qty + use_qty})
                        self.purchase_id.update_subcontract_product_in_source_purchase_order()
        return res

    def search_quant_based_on_product_lot_and_location(self, product_id, location_id, lot_id=None):
        return self.env["stock.quant"].search([('product_id', '=', product_id.id),
                                               ('location_id', '=', location_id.id),
                                               ('lot_id', '=', lot_id.id)])

    def _subcontracted_produce(self, subcontract_details):
        self = self.with_context(is_subcontract=True)
        self.ensure_one()
        return super(StockPicking, self)._subcontracted_produce(subcontract_details)

    def get_total_loss_qty(self, product_ids, move_ids=None):
        move_ids = move_ids or self.move_ids_without_package
        loss_qty = 0
        unit_factor_dict = {}
        for product in product_ids:
            for move in move_ids:
                unit_factor = 0
                if product.id in unit_factor_dict.keys():
                    unit_factor = unit_factor_dict.get(product.id)
                else:
                    bom = move._get_subcontract_bom()
                    line = bom.bom_line_ids.filtered(lambda line: line.product_id.id == product.id)
                    if line:
                        unit_factor = line.product_qty / bom.product_qty
                        unit_factor_dict.update({product.id: unit_factor})
                if unit_factor:
                    loss_qty += ((move.product_uom_qty - move.quantity_done) * unit_factor)
        return loss_qty