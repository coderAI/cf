odoo.define('cf_promotion.sale_order', function(require)
{
    'use strict';
    var FormView = require('web.FormView');
    var Model = require('web.Model');

    FormView.include({
        // render_pager: function($node, options) {
        //     this._super($node, options);
        //     if (this.model === 'sale.order' && this.$el.find('.oe_coupon')){
        //         $('span.oe_coupon.o_form_field').parent().parent().before('<tr><td class="o_td_label"><label class="o_form_label oe_coupon">Coupon</label></td><td><div style="width:30% !important; float:left;"><input class="o_form_input oe_coupon o_form_field" type="text" style="width:100%"></div><div style="width:70%; text-align:left;float:right;padding-left:20px"><button type="button" style="margin-right: 5px" class="btn btn-sm btn-primary btn-default"><span>Apply</span></button><button type="button" class="btn btn-sm btn-primary btn-default"><span>Remove</span></button></div></td></tr>');
        //     }
	    // },

        update_pager: function(dataset, current_min) {
            var self = this;
	        this._super(dataset, current_min);
            debugger;
            if (this.model === 'sale.order' && this.$el.find('.oe_coupon')){
                this.$el.find('.oe_tr_coupon').remove();
                this.$el.find('label.o_form_label.oe_coupon').parent().parent().before('<tr class="oe_tr_coupon"><td class="o_td_label"><label class="o_form_label oe_coupon">Coupon</label></td><td><div style="width:30% !important; float:left;"><input id="oe_input_coupon" class="o_form_input oe_coupon o_form_field" type="text" style="width:100%"></div><div style="width:70%; text-align:left;float:right;padding-left:20px"><button type="button" style="margin-right: 5px" class="btn btn-sm btn-primary btn-default oe_apply_coupon"><span>Apply</span></button><button type="button" class="btn btn-sm btn-primary btn-default oe_remove_coupon"><span>Remove</span></button></div></td></tr>');
                // $("input[name='oe_input_coupon']").val(self.datarecord.coupon || '');
                console.log(self.datarecord.coupon);
                // $('#oe_input_coupon').val(self.datarecord.coupon);
                if (this.$el.find('#oe_input_coupon') && this.$el.find('#oe_input_coupon').length > 0) {
                    this.$el.find('#oe_input_coupon')[0].value = self.datarecord.coupon;
                }
                this.$el.find('.oe_apply_coupon').click(function() {
                    debugger;
                    var model_obj=new Model(self.dataset.model);
                    var order = self.datarecord.id;
                    var coupon = $("input.o_form_input.oe_coupon.o_form_field");
                    if (coupon) {
                        coupon = coupon[0].value;
                    }
                    model_obj.call('update_coupon_and_update_price',[order, coupon || ''],{context:self.dataset.context}).done(function () {});
                });
            }
	    },

        _actualize_mode: function(switch_to) {
            if (switch_to === 'edit' || switch_to === 'create' || switch_to === undefined) {
                this.$el.find('.oe_tr_coupon').hide();
            }
	        return this._super(switch_to);
	    },
    });

});

