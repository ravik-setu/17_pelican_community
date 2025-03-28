odoo.define('mrp_extended.project_data_level_wise_view', function (require) {
'use strict';

var core = require('web.core');
var framework = require('web.framework');
var stock_report_generic = require('stock.stock_report_generic');
var QWeb = core.qweb;
var _t = core._t;
var ProjectDataLevelWise = stock_report_generic.extend({
    events: {
        'click .o_project_data_level_wise_unfoldable': '_onClickUnfold',
        'click .o_project_data_level_wise_foldable': '_onClickFold',
        'click .o_project_data_level_wise_action': '_onClickAction',
        'click .o_project_data_level_wise_show_attachment_action': '_onClickShowAttachment',
    },
    get_html: function() {
        var self = this;
        var args = [
            this.given_context.active_id,
            this.given_context.searchQty || false,
            this.given_context.searchVariant,
        ];
        return this._rpc({
                model: 'project.data.level.wise',
                method: 'get_html',
                args: args,
                context: this.given_context,
            })
            .then(function (result) {
                self.data = result;
                if (! self.given_context.searchVariant) {}
            });
    },
    set_html: function() {
        var self = this;
        return this._super().then(function () {
            self.$('.o_content').html(self.data.lines);
            self.renderSearch();
            self.update_cp();
        });
    },
    render_html: function(event, $el, result){
        if (result.indexOf('project_data_level_wise.document') > 0) {
            if (this.$('.o_project_data_level_wise_has_attachments').length === 0) {
                var column = $('<th/>', {
                    class: 'o_project_data_level_wise_has_attachments',
                    title: 'Files attached to the product Attachments',
                    text: 'Attachments',
                });
                this.$('table thead th:last-child').after(column);
            }
        }
        $el.after(result);
        $(event.currentTarget).toggleClass('o_project_data_level_wise_foldable o_project_data_level_wise_unfoldable fa-caret-right fa-caret-down');
        this._reload_report_type();
    },
    get_products: function(event) {
      var self = this;
      var $parent = $(event.currentTarget).closest('tr');
      var activeID = $parent.data('id');
      var productID = $parent.data('product_id');
      var lineID = $parent.data('line');
      var qty = $parent.data('qty');
      var level = $parent.data('level') || 0;
      return this._rpc({
              model: 'project.data.level.wise',
              method: 'get_products',
              args: [
                  activeID,
                  productID,
                  parseFloat(qty),
                  lineID,
                  level + 1,
              ]
          })
          .then(function (result) {
              self.render_html(event, $parent, result);
          });
    },
    get_lines_data: function(event) {
      var self = this;
      var $parent = $(event.currentTarget).closest('tr');
      var activeID = $parent.data('id');
      var activeModel = $parent.data('model');
      var level = $parent.data('level') || 0;
      return this._rpc({
              model: 'project.data.level.wise',
              method: 'get_lines_data',
              args: [
                  activeID,
                  activeID,
                  activeModel,
                  level + 1,
              ]
          })
          .then(function (result) {
              self.render_html(event, $parent, result);
          });
    },
    update_cp: function () {
        var status = {
            cp_content: {
//                $buttons: this.$buttonPrint,
//                $searchview: this.$searchView
            },
        };
        return this.updateControlPanel(status);
    },
    renderSearch: function () {
//        this.$buttonPrint = $(QWeb.render('project_data_level_wise.button'));
//        this.$buttonPrint.find('.o_project_data_level_wise_print').on('click', this._onClickPrint.bind(this));
//        this.$buttonPrint.find('.o_project_data_level_wise_print_unfolded').on('click', this._onClickPrint.bind(this));
//        this.$searchView = $(QWeb.render('project_data_level_wise.report_mo_con_search', _.omit(this.data, 'lines')));
//        this.$searchView.find('.o_project_data_level_wise_products').on('change', this._onChangeProducts.bind(this));
    },
    _onClickPrint: function (ev) {
        var moIDs = _.map(this.$el.find('.o_project_data_level_wise_foldable').closest('tr'), function (el) {
            return $(el).data('id');
        });
        framework.blockUI();
        var reportname = 'project_extended.project_data_level_wise?docids=' + this.given_context.active_id;
        if (! $(ev.currentTarget).hasClass('o_project_data_level_wise_print_unfolded')) {
            reportname += '&childs=' + JSON.stringify(childBomIDs);
        }
        if ($(ev.currentTarget).hasClass('o_mrp_bom_print_all_variants')) {
            reportname += '&all_variants=' + 1;
        } else if (this.given_context.searchVariant) {
            reportname += '&variant=' + this.given_context.searchVariant;
        }
        var action = {
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': reportname,
            'report_file': 'project_extended.project_data_level_wise',
        };
        return this.do_action(action).then(function (){
            framework.unblockUI();
        });
    },
    _onChangeProducts: function (ev) {
        this.given_context.searchVariant = $(ev.currentTarget).val();
        this._reload();
    },
    _onClickUnfold: function (ev) {
        var redirect_function = $(ev.currentTarget).data('function');
        this[redirect_function](ev);
    },
    _onClickFold: function (ev) {
        this._removeLines($(ev.currentTarget).closest('tr'));
        $(ev.currentTarget).toggleClass('o_project_data_level_wise_foldable o_project_data_level_wise_unfoldable fa-caret-right fa-caret-down');
    },
    _onClickAction: function (ev) {
        ev.preventDefault();
        return this.do_action({
            type: 'ir.actions.act_window',
            res_model: $(ev.currentTarget).data('model'),
            res_id: $(ev.currentTarget).data('res-id'),
            context: {
                'active_id': $(ev.currentTarget).data('res-id')
            },
            views: [[false, 'form']],
            target: 'current'
        });
    },
    _onClickShowAttachment: function (ev) {
        ev.preventDefault();
        var ids = $(ev.currentTarget).data('res-id');
        return this.do_action({
            name: _t('Attachments'),
            type: 'ir.actions.act_window',
            res_model: $(ev.currentTarget).data('model'),
            domain: [['id', 'in', ids]],
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            view_mode: 'kanban,list,form',
            target: 'current',
        });
    },
    _reload: function () {
        var self = this;
        return this.get_html().then(function () {
            self.$('.o_content').html(self.data.lines);
            self._reload_report_type();
        });
    },
    _reload_report_type: function () {
        this.$('.o_project_data_level_wise_bom_cost.o_hidden, .o_project_data_level_wise_prod_cost.o_hidden').toggleClass('o_hidden');
        if (this.given_context.report_type === 'bom_structure') {
           this.$('.o_project_data_level_wise_bom_cost, .o_project_data_level_wise_prod_cost').toggleClass('o_hidden');
        }
    },
    _removeLines: function ($el) {
        var self = this;
        var activeID = $el.data('id');
        _.each(this.$('tr[parent_id='+ activeID +']'), function (parent) {
            var $parent = self.$(parent);
            var $el = self.$('tr[parent_id='+ $parent.data('id') +']');
            if ($el.length) {
                self._removeLines($parent);
            }
            $parent.remove();
        });
    },
});
core.action_registry.add('project_data_level_wise_view', ProjectDataLevelWise);
return ProjectDataLevelWise;
});
