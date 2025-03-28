from pygments.lexer import default

from odoo import fields, Command,models, api, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby
from odoo.exceptions import UserError
from odoo.tests import Form
import logging

_logger = logging.getLogger(__name__)


class SetuProductPackage(models.Model):
    _name = 'setu.product.package'
    _description = 'Product Package'
    _order = 'id desc'

    product_id = fields.Many2one("product.product", string="Product")
    min_weight = fields.Float(string="Min Weight", digits=(4, 4))
    max_weight = fields.Float(string="Max Weight", digits=(4, 4))
    package_lines = fields.One2many("setu.product.package.line", "package_id")
    state = fields.Selection([('new', 'New'), ('done', 'Done'), ('cancel', 'Cancel')], default='new')
    setu_weight = fields.Html()
    name = fields.Char(string="Name")
    lot_id = fields.Many2one("stock.lot", string="Lot", copy=False)
    total_weight = fields.Float(string="Total Weight", compute='_compute_total_weight', store=True, digits=(4, 4))
    put_in_pack_product_id = fields.Many2one('product.product', related="product_id.put_in_pack_product_id", store=True)
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, required=True)
    picking_id = fields.Many2one("stock.picking", string="Internal Transfer")
    product_tracking = fields.Selection(related='put_in_pack_product_id.tracking')
    production_id = fields.Many2one(comodel_name='mrp.production', string='Production')
    outer_box = fields.Boolean(string='Is Outer Box')
    outer_package_line_ids = fields.One2many('setu.outer.package.line', 'package_id')
    outer_package_type_id = fields.Many2one(comodel_name="stock.package.type", string="Package Type", copy=False)
    lot_ids = fields.Many2many('stock.lot', string='Lots')
    product_moves_ids = fields.One2many('stock.move', 'product_package_id')
    package_ids = fields.One2many("stock.quant.package", "setu_package_id", string="Packages")
    no_of_outer_boxes = fields.Integer(string='No of Boxes', default=1)

    @api.constrains('min_weight', 'max_weight')
    def _check_valid_weight(self):
        for rec in self:
            if not rec.outer_box and ((rec.min_weight <= 0 or rec.max_weight <= 0) or rec.min_weight > rec.max_weight):
                raise UserError("Please set valid weight!")

    def do_package_weight(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("setu_packaging.package_weight_wizard_action")
        action['context'] = {'default_package_id': self.id, 'package_lot_id': self.lot_id.id}
        return action

    def button_validate_package(self):
        lot_id = self.lot_id
        if self.product_id.id != self.product_id.put_in_pack_product_id.id:
            self.raise_error_if_put_in_pack_does_not_contain_valid_quantity()
            qty = len(self.package_lines) * self.product_id.qty_in_pack
            mo_id = self.create_and_validate_package_mo(self.product_id, qty)
            mo_id = mo_id.with_context(avoid_reserved_qty_check=True, apply_package_domain=True)
            if self.product_id.tracking != 'none':
                exist_lot = self.env['stock.lot'].search(
                    [('product_id', '=', self.product_id.id), ('name', '=ilike', lot_id.name)], limit=1)
                if not exist_lot:
                    mo_id.action_generate_serial()
                    mo_id.lot_producing_id.name = lot_id.name
                else:
                    mo_id.lot_producing_id = exist_lot.id
            self.reserve_based_on_lot_and_mark_done(mo_id, self.lot_id)
            lot_id = mo_id.lot_producing_id
            self.production_id = mo_id
        try:
            self.create_internal_transfer_and_generate_package(lot_id)
        except Exception as e:
            raise UserError("Error {} comes at the time of creating Internal Transfer".format(e))
        self.package_lines.mapped('quant_package_id').mapped('quant_ids').write(
            {'planning_lot_id': self.lot_id.planning_lot_id.id})
        self.package_ids = self.package_lines.mapped('quant_package_id')
        self.write({'state': 'done'})

    def create_quant_package(self):
        return self.env['stock.quant.package'].create({
            'company_id': self.company_id.id,
            'name': self.lot_id.name
        })

    def action_view_package_moves(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("stock.stock_move_action")
        # action['domain'] = [('package_id', '=', self.id)]
        move_ids = self.production_id.move_raw_ids.filtered(
            lambda move: move.state == 'done') + self.production_id.move_finished_ids.filtered(
            lambda move: move.state == 'done')
        action['domain'] = [('id', 'in', move_ids.ids)]
        if self.outer_box:
            move_ids = self.product_moves_ids
            action['domain'] = [('id', 'in', move_ids.ids)]
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.env['ir.sequence'].next_by_code('setu.product.package') or '/'
        return super(SetuProductPackage, self).create(vals_list)

    def open_weight_scale_wizard(self, setu_weight=False):
        action = self.env.ref('setu_packaging.action_package_weight_scale_wizard').sudo().read()
        vals = {'package_id': self.id}
        if setu_weight:
            vals.update({'setu_weight': setu_weight})
        wiz_data = self.env['package.weight.wizard'].create(vals)
        action[0]['res_id'] = wiz_data.id
        return action[0]

    def process_weight_scale_wizard_data(self, weight=0):
        try:
            weight = float(weight)
        except Exception as e:
            return {'status': False, 'error': e}
        weight = (weight / 1000)
        try:
            self.env["package.weight.wizard"].do_weight_and_update_in_package(weight)
        except Exception as e:
            return {'status': False, 'error': e}
        message = "Weight {} added successfully in package".format(weight)
        return {
            'status': True,
            'message': message,
            'w': message}

    def create_and_validate_package_mo(self, product_id, qty):
        bom_id = self.env["mrp.production.planning"].find_bill_of_material(product_id)
        if not bom_id:
            raise UserError("Please create bill of material with same as box quantity")
        vals = {
            'product_id': product_id.id,
            'bom_id': bom_id.id,
            'product_qty': qty,
            'product_uom_id': bom_id.product_uom_id.id
        }
        mo = self.env["mrp.production"].create(vals)
        mo.action_confirm()
        mo.write({'qty_producing': qty})
        return mo

    def reserve_based_on_lot_and_mark_done(self, mo_id, lot_ids):
        if self.product_tracking != 'none':
            mo_id.do_unreserve()
            self.update_move_qty_based_on_package_weight(mo_id.move_raw_ids)
            self.set_reserve_based_on_lots(mo_id.move_raw_ids, lot_ids)
        for move_line in mo_id.move_line_raw_ids:
            move_line.qty_done = move_line.reserved_uom_qty
        action = mo_id.button_mark_done()
        if action and isinstance(action, dict) and action.get('res_model') == 'mrp.consumption.warning':
            consumption_warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
            consumption_warning.save().action_confirm()

    @api.depends('package_lines')
    def _compute_total_weight(self):
        for rec in self:
            if rec.package_lines:
                rec.total_weight = sum(rec.package_lines.mapped('weight'))
            if rec.outer_package_line_ids:
                rec.total_weight = sum(rec.outer_package_line_ids.mapped('weight'))

    def create_internal_transfer_and_generate_package(self, lot_ids):
        vals = self.prepare_internal_picking_vals()
        picking = self.env["stock.picking"].with_context(apply_package_domain=True).create(vals)
        self.picking_id = picking
        picking.action_confirm()
        for line in self.package_lines:
            line.quant_package_id.write({
                'total_weight': line.weight
            })
            move = self.env["stock.move"].create(self._prepare_stock_move_vals())
            if lot_ids:
                self.set_reserve_based_on_lots(picking.move_ids, lot_ids)
            move._set_quantity_done(self.product_id.qty_in_pack)
            move.move_line_ids.write({'result_package_id': line.quant_package_id.id})
        picking.button_validate()

    def prepare_internal_picking_vals(self):
        picking_type = self.env["stock.picking.type"].search([('code', '=', 'internal')], limit=1)
        location_id = picking_type.default_location_src_id
        location_dest_id = picking_type.default_location_dest_id
        if self.product_id.put_in_pack and hasattr(self.product_id, 'destination_location_id'):
            location_id = self.product_id.destination_location_id or location_id
            location_dest_id = self.product_id.destination_location_id or location_dest_id
        return {
            'picking_type_id': picking_type.id,
            'user_id': False,
            'date': fields.datetime.today(),
            'origin': self.name,
            'location_dest_id': location_dest_id.id,
            'location_id': location_id.id,
            'company_id': self.company_id.id,
        }

    def _prepare_stock_move_vals(self):
        self.ensure_one()
        return {
            'name': _('New Move:') + self.product_id.display_name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.product_id.qty_in_pack,
            'product_uom': self.product_id.uom_id.id,
            'location_id': self.picking_id.location_id.id,
            'location_dest_id': self.picking_id.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'state': self.picking_id.state,
            'picking_type_id': self.picking_id.picking_type_id.id,
            'company_id': self.picking_id.company_id.id,
            'partner_id': self.picking_id.partner_id.id,
        }

    def set_reserve_based_on_lots(self, move_ids, lot_ids):
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        for move in move_ids:
            need = move.product_qty - sum(move.move_line_ids.mapped('reserved_qty'))
            for lot_id in lot_ids:
                if not need:
                    continue
                available_quantity = move._get_available_quantity(move.location_id, lot_id=lot_id, strict=False)
                if float_is_zero(available_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                taken_quantity = move._update_reserved_quantity(need, min(need, available_quantity), move.location_id,
                                                                lot_id, strict=False)
                if float_is_zero(taken_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                if float_is_zero(need - taken_quantity, precision_rounding=move.product_uom.rounding):
                    assigned_moves_ids.add(move.id)
                    break
                need -= taken_quantity
                partially_available_moves_ids.add(move.id)
        StockMove = self.env["stock.move"]
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})

    def raise_error_if_put_in_pack_does_not_contain_valid_quantity(self):
        if self.product_id.id != self.product_id.put_in_pack_product_id.id:
            bom_id = self.env["mrp.production.planning"].find_bill_of_material(self.product_id)
            if bom_id.product_qty % self.product_id.qty_in_pack != 0:
                raise UserError("Please set the quantity in multiple of {} in Bill of Material {}({})".format(
                    self.product_id.qty_in_pack, bom_id.display_name, bom_id.id))

    def button_cancel(self):
        self.write({'state': 'cancel'})

    def update_move_qty_based_on_package_weight(self, move_ids):
        for move in move_ids:
            move.product_uom_qty = sum(self.package_lines.mapped('weight'))

    def button_validate_outer_package(self):
        """
        Author: Ishani Manvar | Date: 05/09/24 | Task No: 814 Create Outer Package
        Purpose: Validating and creating an outer package for the selected inner packages based on lot no.
        """
        product_config_line = self.outer_package_type_id.product_config_line_ids.filtered(
            lambda l: l.product_id == self.product_id)
        location_id = self.product_id.destination_location_id
        domain = [
            ('product_id', '=', self.product_id.id),
            ('package_id.outer_package', '=', False),
            ('location_id', '=', location_id.id),
            ('reserved_quantity', '=', 0),
            ('package_id', '!=', None),
            ('quantity','>',0)
        ]
        if self.lot_ids:
            domain.append(('lot_id', 'in', self.lot_ids.ids))
        product_box_qty = product_config_line.box_quantity * self.no_of_outer_boxes
        quants = self.env['stock.quant'].search(domain)
        total_packages = len(quants.mapped('package_id'))
        if product_box_qty > total_packages:
            raise UserError("You don't have sufficient inner boxes\nRequired Inner Box: {}\nAvailable Inner Box: {}".format(product_box_qty, total_packages))

        total_weight = 0
        vals = self.prepare_internal_picking_vals()
        picking = self.env["stock.picking"].create(vals)
        move_id = self.create_package_move(self.product_id, product_box_qty * self.product_id.qty_in_pack,
                                           src_loc=self.product_id.destination_location_id,
                                           dest_loc=self.product_id.destination_location_id, picking_id=picking)

        packages_in_single_box = 0
        single_box_weight = 0
        for package_no in range(1, int(self.no_of_outer_boxes)+1 ):
            single_box_total_qty = self.product_id.qty_in_pack * product_config_line.box_quantity * package_no
            for quant in quants:
                if not quant.available_quantity:
                    continue
                packages_in_single_box += 1
                move_id._update_reserved_quantity(need=quant.quantity, available_quantity=quant.available_quantity,
                                                  location_id=self.product_id.destination_location_id, lot_id=quant.lot_id,
                                                  package_id=quant.package_id)
                if single_box_total_qty - move_id.quantity <= 0:
                    break
            single_box_weight += quant.package_id.total_weight
            if packages_in_single_box >= product_config_line.box_quantity:
                self._create_outer_package(picking, move_id, single_box_weight, single_box_total_qty)
                total_weight += single_box_weight
                single_box_weight = 0
                packages_in_single_box = 0
                package_no += 1
                if package_no > self.no_of_outer_boxes:
                    break
        move_id._action_done()
        self.write({'total_weight': total_weight})
        outer_label = False
        if self.package_ids:
            self.write({'outer_package_line_ids':[Command.create({
                    'package_id': self.id,
                    'quant_package_id': package.id,
                    'weight': package.total_weight
            }) for package in self.package_ids],})
            self.state = "done"
            outer_label = self.env['setu.product.package.line'].action_generate_label(record=self.outer_package_line_ids, outer_package=True, setu_package_id=self)
        return outer_label

    def _create_outer_package(self, picking, move_ids, total_weight, total_qty):
        picking.write({'move_ids': move_ids})
        move_line_ids = move_ids.move_line_ids.filtered(lambda line:not line.qty_done)
        for line in move_line_ids:
            line.qty_done = line.reserved_qty
        main_package = move_ids.mapped('picking_id')._put_in_pack(move_line_ids)
        main_package.write({'package_type_id': self.outer_package_type_id.id,
                            'outer_package': True,
                            'company_id': self.company_id.id})
        main_package.update_name_based_on_package_type()
        package = move_line_ids.result_package_id[-1]
        if not package.total_weight:
            package.total_weight = total_weight
        if main_package and self.outer_box:
            move_id = self.create_outer_box_product_move()
            outer_box_weight = self.outer_package_type_id.package_product_id.weight
            # main_package.net_weight = total_weight
            total_weight += outer_box_weight
            self.total_weight = total_weight

            _logger.info('package {} total weight is {}'.format(self.name, self.total_weight))

            main_package.weight_uom_name = self.outer_package_type_id.package_product_id.weight_uom_name
            self.write({
                'product_moves_ids': [(4, move_id.id)]})
            move_ids += move_id

        if main_package:
            self.write({'package_ids': [(4, main_package.id)], 'picking_id': picking})


    def create_package_move(self, product, qty, src_loc, dest_loc, picking_id = False):
        """
        Author: Ishani Manvar | Date: 05/09/24 | Task No: 814 Create Outer Package
        Purpose: Creating a package move.
        """
        move_vals = {
            'name': 'created package',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'company_id': self.company_id.id,
            'location_id': src_loc.id,
            'location_dest_id': dest_loc.id,
            'product_uom_qty': qty,
            'picking_id':picking_id and picking_id.id or picking_id
        }
        move_id = self.env['stock.move'].create(move_vals)
        return move_id

    def create_outer_box_product_move(self):
        """
        Author: Ishani Manvar | Date: 06/09/24 | Task No: 814 Create Outer Package
        Purpose: Creating a package move for outer packaging product.
        """
        outer_package_qty = 1
        outer_package_product = self.outer_package_type_id.package_product_id
        if outer_package_product:
            src_loc = outer_package_product.source_location_id.id
            if not src_loc:
                raise UserError(_("Please set the source location of your outer package product {} in the Product Configuration tab.".format(outer_package_product.name)))
            outer_product_quant = self.env['stock.quant'].search(
                [('product_id', '=', outer_package_product.id),
                 ('quantity', '>', 0),
                 ('location_id', '=', src_loc),
                 ('package_id', '=', False)])
            outer_product_qty = sum(outer_product_quant.mapped('available_quantity'))
            if outer_product_qty < 1:
                _logger.info("You don't have sufficient quantity of {}".format(outer_package_product.name))
                raise UserError(_("You don't have sufficient quantity of {}".format(outer_package_product.name)))

            dest_location = self.env['stock.location'].search(
                [('usage', '=', 'production'), ('company_id', '=', self.company_id.id)])
            move_id = self.create_package_move(outer_package_product, outer_package_qty, outer_package_product.source_location_id, dest_location)

            move_id._update_reserved_quantity(need=1, available_quantity=outer_package_qty, location_id=move_id.location_id, strict=True)
            move_id._set_quantity_done(move_id.product_uom_qty)
            move_id.is_done = True
            return move_id

    def action_see_created_packages(self):
        """
        Author: Ishani Manvar | Date: 09/09/24 | Task No: 814 Create Outer Package
        Purpose: Action for seeing all the quant packages.
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_package_view")
        packages = self.package_ids.ids
        action['domain'] = [('id', 'in', packages)]
        return action

