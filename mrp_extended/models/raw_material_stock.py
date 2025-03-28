from odoo import fields, models, api


class RawMaterialStock(models.Model):
    _name = 'raw.material.stock'
    _description = 'Raw Material Stock'

    parent_product_id = fields.Many2one("product.product", string="R.M Size")
    product_id = fields.Many2one("product.product", string="Actual Size")
    name = fields.Char(related="product_id.name")
    grade_id = fields.Many2one("product.grade", related="product_id.grade_id")
    total_qty = fields.Float(string="Total Qty")
    order_qty = fields.Float(string="Order Qty")
    stock_qty = fields.Float(string="Spare Qty")
    process = fields.Char(string="Wire Process")
    current_stage = fields.Char(string="Current Stage")
    remarks = fields.Text(string="Remarks")
    uom_id = fields.Many2one("uom.uom", related="product_id.uom_id")
    lines = fields.One2many("raw.material.stock.line", "raw_material_stock_id", string="Lines")

    @api.model
    def get_views(self, views, options=None):
        self.create_or_update_records()
        return super(RawMaterialStock, self).get_views(views, options)

    def create_or_update_records(self):
        products = self.env["product.product"].search([('grade_id', '!=', False), ('is_raw_material', '=', True)])
        purchase_ids = self.get_drop_ship_and_po_of_subcontract()
        for product in products:
            lines = purchase_ids.subcontract_lines.filtered(lambda line: line.product_id.id == product.id)
            partner_ids = lines.mapped('partner_id')
            order_qty = 0
            rec_id = self.create_record_if_not_exist(product)
            rec_id.lines.unlink()
            available_qty = rec_id.create_line_for_stock_qty(product)
            parent_product_id = self.env["product.product"]
            for partner in partner_ids:
                partner_lines = lines.filtered(lambda line: line.partner_id.id == partner.id)
                partner_qty = sum(partner_lines.mapped('product_qty'))
                partner_lines_po = partner_lines.mapped('purchase_id')
                if partner_lines_po:
                    order_qty += partner_qty
                    if partner_lines_po[0].mapped('order_line')[0].product_id.id:
                        parent_product_id = partner_lines_po[0].mapped('order_line')[0].product_id.id
                    rec_id.lines.create({"parent_product_id": parent_product_id,
                                         "stock_qty": 0,
                                         "order_qty": order_qty, "total_qty": order_qty,
                                         "raw_material_stock_id": rec_id.id,
                                         "product_id": product.id,
                                         "current_stage": partner.name})
            vals = {
                "stock_qty": available_qty,
                "order_qty": order_qty,
                "total_qty": available_qty + order_qty,
                "parent_product_id": parent_product_id or self.get_child_product_based_on_product(product)
            }
            if rec_id.lines:
                vals.update(
                    {"current_stage": ",".join(stage for stage in rec_id.lines.mapped('current_stage'))})
            rec_id.write(vals)

    def create_record_if_not_exist(self, product):
        rec_id = self.search([('product_id', '=', product.id)])
        if not rec_id:
            rec_id = self.create({"product_id": product.id})
        return rec_id

    def create_line_for_stock_qty(self, product_id):
        location_id = product_id.get_product_destination_location()
        available_qty = self.env["mrp.production.planning"].get_available_qty_on_location(product_id, location_id) or 0
        line_obj = self.env["raw.material.stock.line"]
        if available_qty:
            vals = {"raw_material_stock_id": self.id, "stock_qty": available_qty, "product_id": product_id.id,
                    "current_stage": "P.E.P.L",
                    "parent_product_id": self.get_child_product_based_on_product(product_id).id,
                    "total_qty": available_qty}
            line = line_obj.search([('product_id', '=', product_id.id), ('raw_material_stock_id', '=', self.id),
                                    ("current_stage", '=ilike', "P.E.P.L")])
            self.env["raw.material.stock.line"].create(vals) if not line else line.write(vals)
        return available_qty

    def get_drop_ship_and_po_of_subcontract(self):
        subcontracts = self.env["purchase.order"].search(
            [('source_picking_id', '!=', False), ('state', 'not in', ['draft', 'cancel']),
             ('receipt_status', '!=', 'pending'), ('is_subcontract', '=', True)])
        sub_contract_source_pos = subcontracts.mapped('source_picking_id').mapped('purchase_id')
        purchase_orders = self.env["purchase.order"].search(
            [('id', 'not in', sub_contract_source_pos.ids), ('state', 'not in', ['draft', 'cancel']),
             ('drop_to_subcontractor', '=', True)])
        return purchase_orders

    def get_child_product_based_on_product(self, product_id):
        bom_id = product_id.bom_ids
        child_prod = self.env["product.product"]
        if bom_id and bom_id[0].bom_line_ids:
            child_prod = bom_id[0].bom_line_ids[0].product_id
        return child_prod
