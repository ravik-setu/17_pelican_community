/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import DocumentViewer from '@setu_mrp_workorder/components/viewer';

export class MrpWorksheetDialog extends ConfirmationDialog {
    static props = {
        ...ConfirmationDialog.props,
        body: { optional: true },
        worksheetData: [Object, Boolean],
        worksheetText: Object,
    };
    static template = "setu_mrp_workorder.MrpWorksheetDialog";
    static components = {
        ...ConfirmationDialog.components,
        DocumentViewer,
    };
}
