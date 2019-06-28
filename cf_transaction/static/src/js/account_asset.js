odoo.define('cf_transaction.widget', function(require) {
    "use strict";

    var core = require('web.core');
    var WidgetOnButton = require('account_asset.widget').WidgetOnButton;

    var _t = core._t;

    WidgetOnButton.include({
        format: function(row_data, options) {
            debugger;
            this._super.apply(this, arguments);
            this.is_posted = !!row_data.move_posted_check.value;
            this.parent_state = row_data.parent_state.value;
            var class_color = '';
            if (this.is_posted){class_color = 'o_is_posted';}
            else{
                if (row_data.move_check.value){class_color = 'o_unposted';}
            }
            return $('<div/>').append((this.parent_state === 'open')? $('<button/>', {
                type: 'button',
                title: (this.is_posted)? _t('Posted') : _t('Unposted'),
                disabled: !!this.is_posted,
                'class': 'btn btn-sm btn-link fa fa-circle o_widgetonbutton ' + class_color,
            }) : '').html();
        },
    });
    core.list_widget_registry.add("button.widgetonbutton", WidgetOnButton);
});
