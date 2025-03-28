from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    source_picking_id = fields.Many2one("stock.picking", string="Receipt")
    is_subcontract = fields.Boolean(string="Is Subcontract?", copy=False)
    sub_contract_count = fields.Integer(string="Subcontracts", compute="_compute_sub_contract_count")
    dispatch_via = fields.Selection([('road', 'By Road'), ('air', 'By Air')])
    vehicle_number = fields.Char(string="Vehicle No")
    subcontract_process_id = fields.Many2one("subcontract.process", string="Nature")
    remark = fields.Char(string="Remarks")
    subcontract_required = fields.Boolean(string="Go For Subcontract?")
    drop_to_subcontractor = fields.Boolean(string="Drop To Subcontractor")
    subcontract_lines = fields.One2many("purchase.subcontract.line", "purchase_id", string="Subcontract Lines")

    def action_view_subcontract(self):
        purchase_ids = self.search([('source_picking_id', 'in', self.picking_ids._ids)])
        return self._get_action_view_purchase(purchase_ids)

    @api.depends('picking_ids')
    def _compute_sub_contract_count(self):
        for rec in self:
            rec.sub_contract_count = self.search_count([('source_picking_id', 'in', self.picking_ids._ids)])

    def _get_action_view_purchase(self, purchase_ids):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        if len(purchase_ids) > 1:
            action['domain'] = [('id', 'in', purchase_ids.ids)]
        elif purchase_ids:
            form_view = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = purchase_ids.id
        action['context'] = dict(self._context)
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self.env.context.get('is_subcontract', False):
                vals.update({'is_subcontract': True})
        return super(PurchaseOrder, self).create(vals_list)

    @api.onchange('drop_to_subcontractor')
    def onchange_subcontract_required(self):
        for rec in self:
            if rec.drop_to_subcontractor:
                rec.picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'Dropship Subcontractor')],
                                                                            limit=1).id
            else:
                rec.picking_type_id = self.env['stock.picking.type'].search(
                    [('warehouse_id.company_id', '=', self.env.company.id), ('code', '=', 'incoming')], limit=1).id

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for purchase in self:
            if purchase.is_subcontract:
                is_valid_po_subcontract, error_msg = purchase.is_valid_purchase_subcontract_order()
                if not is_valid_po_subcontract and error_msg:
                    raise UserError(error_msg)
                resupply_picks = purchase._get_subcontracting_resupplies()
                # resupply_picks.move_ids.mapped("product_id").mapped("destination_location_id")[0]
                product_ids = self.order_line.mapped("product_id")
                resupply_picks.location_id = product_ids[0].source_location_id
            if purchase.is_subcontract and purchase.source_picking_id:
                pickings = purchase._get_subcontracting_resupplies()
                pickings = pickings.filtered(lambda pick: pick.state not in ['draft', 'cancel', 'done'])
                for picking in pickings:
                    picking.write({'location_id': pickings.location_dest_id.id, 'purchase_id': self.id})
                    picking.do_unreserv_and_reserve_based_on_picking()
                purchase.update_subcontract_product_in_source_purchase_order()
        return res

    def is_valid_purchase_subcontract_order(self):
        """
        Author: Gaurav Vipani | Date: 7th Oct, 2023
        Purpose: This method will be use for check purchase subcontract order is valid as per flow requirement.
        return: bool, str
        """
        self.ensure_one()
        product_ids = self.order_line.mapped("product_id")
        products_not_found_bom = product_ids.filtered(lambda product: not product.bom_ids)
        error_msg = ""
        # if not found BOM
        if products_not_found_bom:
            error_msg = _("Below products not found Bill Of Material. \n - {}".format(
                " , ".join(products_not_found_bom.mapped("name"))))
        products_not_valid_bom = product_ids.bom_ids.filtered(lambda bom: bom.type != "subcontract")
        # if found not valid BOM
        if products_not_valid_bom:
            error_msg = _("Below products Bill Of Material type is not subcontract. \n - {}".format(
                " , ".join(products_not_valid_bom.mapped("product_id").mapped("name"))))
        resupply_route_id = product_ids.env.ref("mrp_subcontracting.route_resupply_subcontractor_mto")
        products_route_not_valid = product_ids.bom_ids.bom_line_ids.filtered(lambda bom_line: resupply_route_id.id
                                                                                              not in bom_line.product_id.route_ids.ids)
        # if products route is not valid
        if products_route_not_valid:
            error_msg = _("Below products component routes is not selected Resupply Subcontractor. \n - {}".format(
                " , ".join(products_route_not_valid.mapped("product_id").mapped("name"))))
        product_source_loc_not_set = product_ids.filtered(lambda product: not product.source_location_id)
        # if product source location is not set
        if product_source_loc_not_set:
            error_msg = _(
                "Below product source location is not set. \n - {}".format(
                    " , ".join(product_source_loc_not_set.mapped("name"))))
        return False if error_msg else True, error_msg

    @api.model
    def default_get(self, fields):
        result = super(PurchaseOrder, self).default_get(fields)
        if self.env.context.get('is_subcontract', False):
            result['is_subcontract'] = True
        return result

    def find_available_purchase_lot(self):
        locations = self.env["stock.location"].search([('is_subcontracting_location', '=', True)])
        stock_quants = self.env["stock.quant"].search(
            [('quantity', '>', 0), ('location_id', 'in', locations._ids)])
        return stock_quants.mapped('lot_id').mapped('purchase_order_ids')

    def update_subcontract_product_in_source_purchase_order(self):
        po = self.source_picking_id.purchase_id
        po.subcontract_lines.unlink()
        line_obj = self.env["purchase.subcontract.line"]
        for line in self.order_line:
            qty = line.product_qty
            if line.qty_received:
                qty = line.qty_received
            line_obj.create({"purchase_id": po.id, "product_id": line.product_id.id, "product_qty": qty,
                             'partner_id': self.partner_id.id})

    def get_tax_amount(self):
        tax_list = self.tax_totals.get('groups_by_subtotal').get('Untaxed Amount')
        data = {}
        for tax in tax_list:
            if tax.get('tax_group_name') in ['SGST', 'CGST']:
                data.update({tax.get('tax_group_name'): tax.get('formatted_tax_group_amount', '')})
        return data

    def _create_picking(self):
        res = super(PurchaseOrder, self)._create_picking()
        for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
            pickings = order.picking_ids.filtered(lambda pick: pick.picking_type_id.code == 'incoming')
            moves = pickings.move_ids.filtered(lambda move: move.product_id.destination_location_id)
            if moves:
                pickings.move_ids._do_unreserve()
                pickings.location_dest_id = moves[0].product_id.destination_location_id.id
        return res

# def do_unreserv_and_reserve_based_on_picking(self, pickings):
#     pickings.move_ids._do_unreserve()
#     lot_ids = self.source_picking_id.mapped('move_line_nosuggest_ids').mapped('lot_id')
#     assigned_moves_ids = OrderedSet()
#     partially_available_moves_ids = OrderedSet()
#     for move in pickings.move_ids:
#         need = move.product_qty - sum(move.move_line_ids.mapped('reserved_qty'))
#         for lot_id in lot_ids.filtered(lambda lot: lot.product_id.id == move.product_id.id):
#             if not need:
#                 continue
#             available_quantity = move._get_available_quantity(move.location_id, lot_id=lot_id, strict=True)
#             if float_is_zero(available_quantity, precision_rounding=move.product_uom.rounding):
#                 continue
#             taken_quantity = move._update_reserved_quantity(need, min(need, available_quantity), move.location_id,
#                                                             lot_id, )
#             if float_is_zero(taken_quantity, precision_rounding=move.product_uom.rounding):
#                 continue
#             if float_is_zero(need - taken_quantity, precision_rounding=move.product_uom.rounding):
#                 assigned_moves_ids.add(move.id)
#                 break
#             partially_available_moves_ids.add(move.id)
#     StockMove = self.env["stock.move"]
#     StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
#     StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
