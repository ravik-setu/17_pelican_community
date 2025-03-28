from odoo import fields, models, api
from odoo.tools.misc import xlsxwriter
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class AccountReportWizard(models.TransientModel):
    _inherit = 'account.report.wizard'
    def prepare_tds_taxes_report_vals(self):
        partner_ids = self.env['res.partner'].search([('apply_tds', '=', True)])
        move_ids = self.env['account.move'].search(
            [('partner_id', 'in', partner_ids._ids), ('move_type', 'in', ['in_invoice', 'in_refund']),
             ('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date), ('state', '=', 'posted')])
        move_partners = move_ids.mapped('partner_id')
        vals = {}
        for partner in move_partners:
            partner_moves = move_ids.filtered(lambda move: move.partner_id.id == partner.id)
            in_move = partner_moves.filtered(lambda move: move.move_type == 'in_invoice')
            in_move_refund = partner_moves.filtered(lambda move: move.move_type == 'in_refund')
            amount_untaxed = sum(in_move.mapped('invoice_line_ids').mapped('price_subtotal')) - sum(
                in_move_refund.mapped('invoice_line_ids').mapped('price_subtotal'))
            unpaid_tds_move_lines = partner_moves.invoice_line_ids.filtered(lambda line: partner.tds_tax_id.id not in
                                                                                         line.tax_ids.ids)
            unpaid = sum(unpaid_tds_move_lines.mapped('price_subtotal'))
            paid = amount_untaxed - unpaid
            tds_amount = unpaid_tds = paid_tds = 0
            tax_percent = abs(partner.tds_tax_id.amount)
            tds_amount += round((tax_percent * amount_untaxed) / 100, 4)
            unpaid_tds += round((tax_percent * unpaid) / 100, 4)
            paid_tds += round((tax_percent * paid) / 100, 4)
            net_tds_to_be_paid = paid_tds

            tds_tag_ids = (partner.tds_tax_id.invoice_repartition_line_ids.filtered(
                lambda line: line.repartition_type == 'tax').mapped('tag_ids'))
            for tag_id in tds_tag_ids:
                tds_tag_name = tag_id.name.strip("-") or tag_id.name.strip("+")
                tax_group_name_id = self.env['account.report.expression'].search([('formula', '=like', tds_tag_name)])
                if tax_group_name_id.report_line_name not in vals.keys():
                    vals.update({tax_group_name_id.report_line_name: []})
                vals[tax_group_name_id.report_line_name].append({'partner_details': partner.name or "",
                                                                 'pan_no': partner.l10n_in_pan or "",
                                                                 'amount_untaxed': amount_untaxed,
                                                                 'percentage': tax_percent,
                                                                 'tds_amount': tds_amount,
                                                                 'deductable_tds': unpaid_tds,
                                                                 'deducted_tds': paid_tds,
                                                                 'net_tds_to_be_paid': net_tds_to_be_paid})
        return vals
    def download_and_design_tds_taxes_report(self):
        """
        Author: Gaurav Vipani | Date: 13th March, 2024
        Purpose: This method will be used for download and design TDS Tax report.
        """
        try:
            tds_report_vals = self.prepare_tds_taxes_report_vals()
        except Exception as e:
            _logger.info("====== ERROR COMES FROM DOWNLOAD TDS TAX REPORT's PREPARE VALS - {}".format(e))
        file_pointer = BytesIO()
        workbook = xlsxwriter.Workbook(file_pointer)
        worksheet = workbook.add_worksheet('TDS Report')
        company_heading_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 5, 'font_size': 11, })
        company_address_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 2, 'font_size': 9})
        report_heading_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 5, 'font_size': 10})
        date_heading_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 3, 'font_size': 9})
        report_hearder_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 4, 'font_size': 9})
        report_info_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9})
        report_tax_heading_format = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'bold': 3,
                                                         'font_size': 9})
        date_heading = "DATE - {} TO {}".format(self.start_date.strftime("%d-%m-%Y"),
                                                self.end_date.strftime("%d-%m-%Y"))
        worksheet.merge_range("A1:K2", self.company_id.name, company_heading_format)
        worksheet.merge_range("A3:K3", self.company_id.street, company_address_format)
        worksheet.merge_range("A4:K4",
                              "{}, {} - ({}), {}, {}".format(self.company_id.street2, self.company_id.city,
                                                             self.company_id.zip, self.company_id.state_id.name,
                                                             self.company_id.country_id.name),
                              company_address_format)
        worksheet.merge_range("A5:K5", "TDS REPORT".format(self.start_date, self.end_date),
                              report_heading_format)
        worksheet.merge_range("A6:K6", date_heading, date_heading_format)
        # Write Excel File Header
        header_list = ['Sr.', 'Party Name', 'Pan Number', 'Total Voucher Assessable Amt', 'TDS Assessable Amount',
                       'TDS %', 'TDS Amount', 'Total Deductible TDS', 'Total Deducted TDS', 'Paid TDS',
                       'Net TDS to be Paid']
        col_width_list = [5, 40, 20, 15, 15, 15, 15, 15, 15, 15, 15]
        header_row_no = 6
        header_col_no = 0
        for header, col_width in zip(header_list, col_width_list):
            worksheet.write(header_row_no, header_col_no, header, report_hearder_format)
            worksheet.set_column(header_col_no, header_col_no, col_width)
            header_col_no += 1
        # Write TDS Report Data
        row = header_row_no + 1
        col_index = {'partner_details': 1, 'pan_no': 2, 'amount_untaxed': 4, 'percentage': 5, 'tds_amount': 6,
                     'deductable_tds': 7, 'deducted_tds': 8, 'net_tds_to_be_paid': 10, 'total_amount_untaxed': 4,
                     'total_tds_amount': 6, 'total_deductable_tds': 7, 'total_deducted_tds': 8,
                     'total_net_tds_to_be_paid': 10}
        all_tax_totals = {'total_amount_untaxed': 0, 'total_tds_amount': 0, 'total_deductable_tds': 0,
                              'total_deducted_tds': 0, 'total_net_tds_to_be_paid': 0}
        for tds_tax, tax_vals in tds_report_vals.items():
            worksheet.merge_range(row, 0, row, len(header_list) - 1, "Nature Of Payment - {}".format(tds_tax),
                                  report_tax_heading_format)
            row += 1
            count = 1
            taxwise_totals = {'total_amount_untaxed': 0, 'total_tds_amount': 0, 'total_deductable_tds': 0,
                              'total_deducted_tds': 0, 'total_net_tds_to_be_paid': 0}
            for vals in tax_vals:

                # Write Tax Details
                for key, val in vals.items():
                    worksheet.write(row, 0, count, report_info_format)
                    worksheet.write(row, col_index.get(key), val, report_info_format)
                taxwise_totals['total_amount_untaxed'] += vals['amount_untaxed']
                taxwise_totals['total_tds_amount'] += vals['tds_amount']
                taxwise_totals['total_deductable_tds'] += vals['deductable_tds']
                taxwise_totals['total_deducted_tds'] += vals['deducted_tds']
                taxwise_totals['total_net_tds_to_be_paid'] += vals['net_tds_to_be_paid']
                count += 1
                row += 1

            # Write Taxwise Total
            worksheet.merge_range(row, 0, row, 2, "Total", report_heading_format)
            for key, val in taxwise_totals.items():
                worksheet.write(row, col_index.get(key), val, report_heading_format)
                all_tax_totals[key] += val
            row +=1

        # Write All Tax Total Details
        worksheet.merge_range(row, 0, row, 2, "Total", report_heading_format)
        for key, vals in all_tax_totals.items():
            worksheet.write(row, col_index.get(key), vals, report_heading_format)
        row+=1
        workbook.close()
        file_name = "{}to{}_TDS_Report.xlsx".format(self.start_date.strftime("%d-%m-%Y"),
                                                    self.end_date.strftime("%d-%m-%Y"))
        file_pointer.seek(0)
        file_data = base64.encodebytes(file_pointer.read())
        self.write({'datas': file_data})
        file_pointer.close()
        return {
            'name': 'TDS Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_xlsx_document?model=account.report.wizard&field=datas&id={}&filename={}'.format(
                self.id, file_name),
            'target': 'self',
        }