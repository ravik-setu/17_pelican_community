from odoo import fields, models, api


class SubcontractSpecificationWizard(models.TransientModel):
    _name = 'subcontract.specification.wizard'
    _description = 'Subcontract Specification'

    purchase_line_id = fields.Many2one('purchase.order.line')
    grade = fields.Char(string='Grade')
    heat_no = fields.Char(string='Heat No')
    hrc = fields.Char(string="HRC")
    lot_id = fields.Char(string="Lot No")
    drawing_size = fields.Char(string="Drawing Size")
    bundle_size = fields.Char(string="Bundle Size")
    uts = fields.Char(string="UTS")
    bundle_id = fields.Char(string="Bundle ID")
    bundle_od = fields.Char(string="Bundle OD")
    process_specification = fields.Text(string="PPD/SAPPD/SADSAPPD")

    def add_specification_in_line(self):
        name = '{} \nSpecification'.format(self.purchase_line_id.product_id.name)
        vals = [{
            'Grade': self.grade, 'Heat No': self.heat_no, 'HRC': self.hrc, 'Lot No': self.lot_id},
            {'process_specification': self.process_specification},
            {'Drawing Size': self.drawing_size, 'Bundle Size': self.bundle_size, 'UTS': self.uts},
            {'Bundle ID': self.bundle_id, 'Bundle OD': self.bundle_od}]

        for item in vals:
            for key, value in item.items():
                if value:
                    name += "\n({})\n{}".format(
                        self.purchase_line_id.order_id.subcontract_process_id.name,
                        self.process_specification) if key == 'process_specification' else "{}".format(
                        "\n{} : {}".format(key, value) if name else "{} : {}".format(key, value))
        self.purchase_line_id.name = name
