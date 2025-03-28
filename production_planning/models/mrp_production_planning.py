from typing import final

from odoo import models, fields, api, _
import base64, math
from io import BytesIO
from odoo.tools.misc import xlsxwriter
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


class ProductionPlanning(models.Model):
    _name = 'mrp.production.planning'
    _description = "Production Planning"
    _order = 'id desc'

    name = fields.Char("Name", default=lambda x: _('New'))
    order_date = fields.Date(string="Order Date")
    sale_order_ref = fields.Char(string="Sr. No from qc sheet")
    customer_id = fields.Many2one("res.partner", string="Customer")
    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine Name")
    product_id = fields.Many2one("product.product", string="Product")
    product_tmpl_id = fields.Many2one("product.template", related="product_id.product_tmpl_id")
    standard_drawing = fields.Char("Standard/Drawing")
    marking = fields.Char(string="Marking")
    production_kg = fields.Float(string="Production Qty. Kg")
    rm_draw_size = fields.Char("")
    state = fields.Selection([
        ('draft', 'Draft'), ('confirm', 'Confirm'), ('in_progress', 'Inprogress'), ('done', 'Done'),
        ('cancel', 'Cancel')
    ], default='draft')
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0',
        help="Planing will process first with the highest priorities.")
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, required=True)
    surface_finish = fields.Char(string="Surface Finish")
    mo_ids = fields.One2many("mrp.production", "planning_id", "Manufacturing Orders")
    planning_lines = fields.One2many("mrp.production.planning.line", "planning_id", string="Lines")
    qty = fields.Float(string="Quantity")
    lot_id = fields.Many2one("planning.lot", string="Serial Number/ Lot", copy=False)
    available_qty = fields.Float(string="Available Qty", compute='compute_available_qty')
    lot_name = fields.Char(string='Serial Number / Lot', copy=False)
    excel_file_data = fields.Binary()
    def action_confirm(self):
        """
        Added By : Ravi Kotadiya | On : Apr-14-2023 | Task : 2114
        Use : To find the child bom and create lines with child boms
        """
        self.ensure_one()
        self.planning_lines.unlink()
        lst = []
        bom_id = self.find_bill_of_material(self.product_id.put_in_pack_product_id)
        if not bom_id:
            raise UserError(
                "No Bill of Material found for product {}".format(self.product_id.put_in_pack_product_id.name))
        line_product_ids = []
        bom_ids = self.find_all_mo_type_bom(bom_id)
        for bom_id in bom_ids:
            if bom_id.type == 'packaging':
                continue
            product_id = bom_id.product_id or bom_id.product_tmpl_id.product_variant_ids[0]
            qty = 0 if product_id.id != self.product_id.id else self.production_kg
            if product_id.id == self.product_id.put_in_pack_product_id.id:
                available_qty = sum(
                    self.get_available_qty_on_location(self.product_id, find_quant=True).mapped('quant_qty'))
            else:
                available_qty = self.get_available_qty_on_location(product_id)
            if product_id and product_id not in line_product_ids:
                lst.append((0, 0, {'product_id': product_id.id, 'bom_id': bom_id.id,
                                   'available_qty': available_qty, 'qty': qty}))
                line_product_ids.append(bom_id.product_id.id)
        if lst:
            self.write({'planning_lines': lst, 'state': 'confirm'})

    def finish_planning(self):
        for rec in self:
            inprogress_mos = rec.mo_ids.filtered(lambda x: x.state not in ['done', 'cancel'])
            if inprogress_mos:
                raise UserError(
                    _('Please Validate Given Manufacturing Orders {}'.format(
                        '\n'.join(mo.name for mo in inprogress_mos))))
            else:
                self.state = 'done'

    def find_bill_of_material(self, product_id=False, type=False):
        domain = ['|', ('product_id', '=', product_id.id), ('product_tmpl_id', '=', product_id.product_tmpl_id.id)]
        domain.append(('type', '=', type)) if type else (('type', '!=', 'phantom'))
        return self.env["mrp.bom"].search(domain, limit=1)

    def find_all_mo_type_bom(self, bom_id):
        bom_ids = bom_id
        child_lines = bom_id.bom_line_ids
        while (child_lines):
            for line in child_lines:
                bom_id = self.find_bill_of_material(line.product_id, type='normal')
                if not bom_id:
                    bom_id = self.find_bill_of_material(line.product_id)
                if bom_id:
                    if bom_id.type == 'normal':
                        bom_ids += bom_id
                    child_lines += bom_id.bom_line_ids
                child_lines -= line
        return bom_ids

    def action_create_mo(self):
        """
        Added By : Ravi Kotadiya | On : Apr-14-2023 | Task : 2114
        Use : To create manufacturing order based on the planning lines
        """
        mrp_obj = self.env['mrp.production']
        lines = self.planning_lines.filtered(lambda line: line.qty > 0 and not line.product_id.id == self.product_id.id)
        if not lines:
            raise UserError("Please Add Quantity into lines!")
        if not self.lot_id:
            raise UserError("Please create Serial/Lot for planning!")
        for line in self.planning_lines:
            if line.qty <= 0:
                continue
            vals = {'product_id': line.product_id.id,
                    'planning_id': self.id,
                    'product_tmpl_id': line.product_id.product_tmpl_id.id,
                    'product_uom_id': line.product_id.uom_id.id,
                    'product_qty': line.qty,
                    'bom_id': line.bom_id.id,
                    'workcenter_id': line.workcenter_id.id}
            try:
                mo_id = mrp_obj.create(vals)
                mo_id._compute_workorder_ids()
                if line.workcenter_id:
                    mo_id.workorder_ids.write({'workcenter_id': line.workcenter_id.id})
                mo_id.action_confirm()
                _logger.info(
                    "MO {}: {} created for planing{}:{} with Qty: {}".format(mo_id.id, mo_id.name, self.id, self.name,
                                                                             line.qty))
                self.state = 'in_progress'
            except Exception as e:
                _logger.info(
                    "Error {} comes at the time of creating MO for product {} Qty and planing {}".format(e,
                                                                                                         line.product_id.name,
                                                                                                         line.qty,
                                                                                                         self.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' not in vals or vals['name'] == _('New'):
                vals['name']= self.env['ir.sequence'].next_by_code('mrp.production.planning') or ''
        res = super(ProductionPlanning, self).create(vals_list)
        return res

    def cancel_planning(self):
        """
        Added By : Ravi Kotadiya | On : Apr-14-2023 | Task : 2114
        Use: Cancel Planning and related manufacturing orders
        """
        for rec in self:
            mo_ids = rec.mo_ids.filtered(lambda mo: mo.state != 'cancel')
            if mo_ids:
                raise UserError(
                    _('Sorry you can not cancel Planning given manufacturing order is created {}'.format(
                        '\n'.join(mo.name for mo in mo_ids))))
            rec.mo_ids.action_cancel()
            rec.state = 'cancel'

    def get_available_qty_on_location(self, product_id, location_id=False, find_quant=False):
        if hasattr(self.env["product.product"], 'destination_location_id'):
            location_id = location_id or product_id.destination_location_id
        quants = self.env["stock.quant"]._gather(product_id, location_id)
        if find_quant:
            return quants
        return sum(quants.mapped('available_quantity'))

    def get_lines_available_qty(self):
        for rec in self.planning_lines:
            if rec.product_id.id == rec.planning_id.product_id.put_in_pack_product_id.id:
                quants = self.get_available_qty_on_location(rec.product_id, find_quant=True)
                rec.available_qty = sum(quants.mapped('available_quantity'))
                rec.available_qty_in_pcs = sum(quants.mapped('quant_qty'))
            else:
                rec.available_qty = self.get_available_qty_on_location(rec.product_id)
    def action_generate_serial(self):
        if not self.lot_name:
            raise UserError("Please fill Serial/Lot for planning!")
        else:
            self.lot_id = self.env["planning.lot"].search([('name', '=', self.lot_name)])
            if not self.lot_id:
                self.lot_id = self.env["planning.lot"].action_generate_serial(self)
                self.lot_id.name = self.lot_name

    @api.onchange('product_id')
    def compute_available_qty(self):
        for rec in self:
            rec.available_qty = rec.get_total_available_qty()

    @api.onchange('qty')
    def onchange_qty(self):
        for rec in self:
            if rec.product_id.put_in_pack_product_id and rec.qty:
                rec.production_kg = rec.qty * rec.product_id.put_in_pack_product_id.weight
            else:
                rec.production_kg = rec.qty

    def get_total_available_qty(self):
        qty = self.get_available_qty_on_location(self.product_id)
        if self.product_id.id != self.product_id.put_in_pack_product_id.id:
            available_qty = self.get_available_qty_on_location(self.product_id.put_in_pack_product_id)
            if self.product_id.uom_id.category_id.id != self.product_id.put_in_pack_product_id.uom_id.category_id.id:
                available_qty = available_qty * self.product_id.qty_in_pack
            qty += available_qty
        return math.ceil(qty)

    def find_all_bom(self, bom_id):
        bom_ids = bom_id
        child_lines = bom_id.bom_line_ids
        while (child_lines):
            for line in child_lines:
                bom_id = self.find_bill_of_material(line.product_id)
                if bom_id:
                    bom_ids += bom_id
                    child_lines += bom_id.bom_line_ids
                child_lines -= line
        return bom_ids

    def action_generate_final_test_report(self):
        file_name = "Final_Test_Report_{}{}".format(str(self.name), ".xlsx")
        file_pointer = BytesIO()
        workbook = xlsxwriter.Workbook(file_pointer)
        worksheet = workbook.add_worksheet('{}'.format(self.name))

        inspection_sheet_ids = self.env['quality.check.sheet'].search([('production_id', 'in', self.mo_ids.ids)])
        component_lot_ids = self.mo_ids.move_line_raw_ids.lot_id
        internal_and_receipt_sheet_ids = self.env['quality.check.sheet'].search(
            [('lot_id', '=', component_lot_ids.ids)])
        quality_process_ids = self.env['quality.process'].search([], order='sequence').filtered(
            lambda p: p.is_include_in_report)
        final_inspection_sheet_ids = (inspection_sheet_ids | internal_and_receipt_sheet_ids).filtered(
            lambda s: s.plan_id.quality_process_id.id in quality_process_ids.ids and s.state in ['accept',
                                                                                                 'released'])
        if not final_inspection_sheet_ids:
            raise UserError("There are no quality check sheets to include in the report!")

        row_no = self.create_static_header(workbook, worksheet, final_inspection_sheet_ids)

        sheet_to_include = {}
        for process in quality_process_ids:
            sheet_id = final_inspection_sheet_ids.filtered(lambda s: s.plan_id.quality_process_id == process)[:1]
            if process not in sheet_to_include and sheet_id:
                sheet_to_include.update({process: sheet_id})
        for process, sheet in sheet_to_include.items():
            row_no = self.create_process_headers_and_data(row_no, workbook, worksheet, process, sheet)
            row_no = row_no

        last_row_no = self.create_footer(workbook, worksheet, row_no)
        worksheet.set_column(15, 1, 13)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodebytes(file_pointer.read())
        self.write({'excel_file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Final Test Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_final_test_report?model=mrp.production.planning&field=excel_file_data&id={}&filename={}'.format(
                self.id, file_name),
            'target': 'self',
        }

    def create_static_header(self, workbook, worksheet, sheets):
        merge_format = workbook.add_format({'bold': 8, 'border': 2, 'font_size': 25,
                                            'align': 'center', 'valign': 'vcenter'})
        worksheet.merge_range(0, 0, 1, 15, 'PELICAN', merge_format)
        worksheet.set_row(0, 40)
        merge_format = workbook.add_format({'bold': 4, 'border': 2, 'font_size': 18,
                                            'align': 'center', 'valign': 'vcenter'})
        worksheet.merge_range(2, 0, 2, 15, 'Final Test Report', merge_format)
        worksheet.set_row(2, 20)

        merge_format = workbook.add_format({'border': 2, 'font_size': 12,
                                            'align': 'left', 'valign': 'vcenter'})
        bold_format = workbook.add_format({'bold': 10, 'font_size': 12, 'align': 'left', 'valign': 'vcenter'})

        worksheet.merge_range(3, 0, 3, 4, 'Engitech Product Code: {}'.format(self.product_id.default_code),
                              merge_format)
        worksheet.write_rich_string('A4', bold_format, 'Engitech Product Code:', merge_format, ' {}'.format(self.product_id.default_code))

        worksheet.merge_range(4, 0, 4, 4, 'Customer Part No.: -', merge_format)
        worksheet.write_rich_string('A5', bold_format, 'Customer Part No.:', merge_format, '   -')

        worksheet.merge_range(5, 0, 5, 4, 'Part Description: {}'.format(self.product_id.name),
                              merge_format)
        worksheet.write_rich_string('A6', bold_format, 'Part Description:', merge_format, ' {}'.format(self.product_id.name))

        worksheet.merge_range(6, 0, 6, 4, 'Invoice/Challan No.: -', merge_format)
        worksheet.write_rich_string('A7', bold_format, 'Invoice/Challan No.:', merge_format, '   -')

        worksheet.merge_range(7, 0, 7, 4, 'Customer Name: {}'.format(self.customer_id.name),
                              merge_format)
        worksheet.write_rich_string('A8', bold_format, 'Customer Name:', merge_format, ' {}'.format(self.customer_id.name))

        worksheet.merge_range(3, 5, 3, 9, 'Prod. Lot No.: {}'.format(self.lot_name),
                              merge_format)
        worksheet.write_rich_string('F4', bold_format, 'Prod. Lot No.:', merge_format,
                                    ' {}'.format(self.lot_name))

        worksheet.merge_range(4, 5, 4, 9, 'Product Finish: {}'.format(self.product_id.name),
                              merge_format)
        worksheet.write_rich_string('F5', bold_format, 'Product Finish:', merge_format,
                                    ' {}'.format(self.product_id.name or ' -'))

        worksheet.merge_range(5, 5, 5, 9, 'Product Grade: {}'.format(self.product_id.grade_id.name),
                              merge_format)
        worksheet.write_rich_string('F6', bold_format, 'Product Grade:', merge_format,
                                    ' {}'.format(self.product_id.grade_id.name or ' -'))

        raw_material_product = self.planning_lines.bom_id.bom_line_ids.product_id.filtered(lambda p: p.is_raw_material)
        worksheet.merge_range(6, 5, 6, 9, 'R.M Specification: {}'.format(raw_material_product.name),
                              merge_format)
        worksheet.write_rich_string('F7', bold_format, 'R.M Specification:', merge_format,
                                    ' {}'.format(raw_material_product.name or ' -'))

        worksheet.merge_range(7, 5, 7, 9, 'Standard: {}'.format(self.product_id.name),
                              merge_format)
        worksheet.write_rich_string('F8', bold_format, 'Standard:', merge_format,
                                    ' {}'.format(self.product_id.name or ' -'))

        sample_size = sheets[:1].sampled_quantity
        worksheet.merge_range(3, 10, 3, 15, 'Date: {}'.format(self.order_date),
                              merge_format)
        worksheet.write_rich_string('K4', bold_format, 'Date:', merge_format,
                                    ' {}'.format(self.order_date))

        worksheet.merge_range(4, 10, 4, 15, 'Invoice Date: -', merge_format)
        worksheet.write_rich_string('K5', bold_format, 'Invoice Date:', merge_format, '   -')

        worksheet.merge_range(5, 10, 5, 15, 'Sample Size: {}'.format(sample_size),
                              merge_format)
        worksheet.write_rich_string('K6', bold_format, 'Sample Size:', merge_format,
                                    ' {}'.format(sample_size or ' -'))

        worksheet.merge_range(6, 10, 6, 15, 'Sales Order No.: -', merge_format)
        worksheet.write_rich_string('K7', bold_format, 'Sales Order No.:', merge_format, '   -')

        worksheet.merge_range(7, 10, 7, 15, 'Report No.: {}'.format(self.id),
                              merge_format)
        worksheet.write_rich_string('K8', bold_format, 'Report No.:', merge_format,
                                    ' {}'.format(self.id))

        return 7

    def create_process_headers_and_data(self, row_no, workbook, worksheet, process, sheet):
        row_no += 1
        merge_format = workbook.add_format({'bold': 4, 'border': 2, 'font_size': 11,
                                            'align': 'center', 'valign': 'vcenter'})
        worksheet.merge_range(row_no, 0, row_no, 15, '{}'.format(process.name), merge_format)
        worksheet.set_row(row_no, 30)
        row_no += 1
        test_type = sheet.quality_check_ids[:1].test_type
        if test_type == 'passfail':
            headers = {
                'nature_of_test': "Nature Of Test",
                'measurement_technique': "Evaluation/Measurement Technique",
                'specified': "Specified",
                'observation': "Observation",
                'remarks': "Remarks",
            }
            col = 0
            for code, header in headers.items():
                if code != 'remarks':
                    merge_format = workbook.add_format({'bold': 2, 'border': 2, 'font_size': 11,
                                                        'align': 'center', 'valign': 'vcenter'})
                    worksheet.merge_range(row_no, col, row_no, col+2, header, merge_format)
                    worksheet.set_row(row_no, 20)
                    col = col+3
                if code == 'remarks':
                    merge_format = workbook.add_format({'bold': 2, 'border': 2, 'font_size': 11,
                                                        'align': 'center', 'valign': 'vcenter'})
                    worksheet.merge_range(row_no, col, row_no, 15, header, merge_format)
                    worksheet.set_row(row_no, 20)
        elif test_type == 'measure':
            headers = {
                'nature_of_test': "Nature Of Test",
                'min': "Min",
                'max': "Max",
                'observation': "Observation",
            }
            col = 0
            for code, header in headers.items():
                if code != 'observation':
                    merge_format = workbook.add_format({'bold': 2, 'border': 2, 'font_size': 11,
                                                        'align': 'center', 'valign': 'vcenter'})
                    worksheet.merge_range(row_no, col, row_no, col + 2, header, merge_format)
                    worksheet.set_row(row_no, 20)
                    col = col + 3
                if code == 'observation':
                    merge_format = workbook.add_format({'bold': 2, 'border': 2, 'font_size': 11,
                                                        'align': 'center', 'valign': 'vcenter'})
                    worksheet.merge_range(row_no, col, row_no, 15, header, merge_format)
                    worksheet.set_row(row_no, 20)

        for quality_check in sheet.quality_check_ids:
            row_no += 1
            row_no = self.get_quality_check_data(row_no, workbook, worksheet, quality_check, test_type)
        if sheet.remarks:
            row_no += 1
            merge_format = workbook.add_format({'border': 2, 'font_size': 11,
                                                'align': 'center', 'valign': 'vcenter'})
            bold_format = workbook.add_format({'bold': 1, 'border': 2, 'font_size': 11,
                                                'align': 'center', 'valign': 'vcenter'})
            worksheet.merge_range(row_no, 0, row_no, 15, 'Remarks: {}'.format(sheet.remarks), merge_format)
            worksheet.write_rich_string(row_no, 0, bold_format, 'Remarks:', merge_format,
                                        ' {}'.format(sheet.remarks))
        return row_no

    def get_quality_check_data(self, row_no, workbook, worksheet, quality_check, test_type):
        if test_type == 'measure':
            data_dict = {'nature_of_test': quality_check.title or ' -',
                         'min_tol': quality_check.tolerance_min  or ' -',
                         'max_tol': quality_check.tolerance_max  or ' -',
                         'observation': quality_check.measure  or ' -'}
            col = 0
            for code, data in data_dict.items():
                if code != 'observation':
                    merge_format = workbook.add_format({'border': 2, 'font_size': 11,
                                                        'align': 'center', 'valign': 'vcenter'})
                    worksheet.merge_range(row_no, col, row_no, col + 2, data, merge_format)
                    col = col + 3
                if code == 'observation':
                    merge_format = workbook.add_format({'border': 2, 'font_size': 11,
                                                        'align': 'center', 'valign': 'vcenter'})
                    worksheet.merge_range(row_no, col, row_no, 15, data, merge_format)
        if test_type == 'passfail':
            data_dict = {'nature_of_test': quality_check.title  or ' -',
                         'measurement_technique': quality_check.point_id.test_method_id.name  or ' -',
                         'specified': quality_check.specified  or ' -',
                         'observation': quality_check.observation  or ' -',
                         'remarks': quality_check.remarks  or ' -'}
            col = 0
            for code, data in data_dict.items():
                if code != 'remarks':
                    merge_format = workbook.add_format({'border':2, 'font_size': 11,
                                                        'align': 'center', 'valign': 'vcenter'})
                    worksheet.merge_range(row_no, col, row_no, col + 2, data, merge_format)
                    col = col + 3
                if code == 'remarks':
                    merge_format = workbook.add_format({'border': 2, 'font_size': 11,
                                                        'align': 'center', 'valign': 'vcenter'})
                    worksheet.merge_range(row_no, col, row_no, 15, data, merge_format)
        return row_no

    def create_footer(self, workbook, worksheet, row_no):
        merge_format = workbook.add_format({'bold': 2, 'border': 2, 'font_size': 10,
                                            'align': 'left', 'valign': 'vcenter'})
        worksheet.merge_range(row_no + 1, 0, row_no + 1, 15, 'Final Remarks: 1.) Chemical,mechanical and physical properties tested as per standard ISO 898.', merge_format)
        worksheet.merge_range(row_no + 2, 0, row_no + 2, 15, 'This is to certify that the above mentioned products were inspected for dimensional & physical characteristics ,chemical compositions and were found to be acceptable as per specifications.', merge_format)
        worksheet.merge_range(row_no + 3, 0, row_no + 3, 15, 'This is a computer generated report and hence no signature required.', merge_format)
        return row_no+3
