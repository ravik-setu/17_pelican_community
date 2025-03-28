/** @odoo-module **/

import { Component } from "@odoo/owl";

export class GanttPopover extends Component {
    onClick() {
        this.props.button.onClick();
        this.props.close();
    }
}
GanttPopover.template = "setu_web_gantt.GanttPopover";
GanttPopover.props = ["title", "template?", "context", "close", "button?"];
GanttPopover.defaultProps = { template: "setu_web_gantt.GanttPopover.default" };
