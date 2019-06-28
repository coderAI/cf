odoo.define('cf_transaction.ListView', function (require) {"use strict";

    var ListView = require('web.ListView').List;
    ListView.include({
        init: function(group, opts){
            var self = this;
            this._super(group, opts);
            this.$current = $('<tbody>')
                .delegate('input[readonly=readonly]', 'click', function (e) {
                /*
                    Against all logic and sense, as of right now @readonly
                    apparently does nothing on checkbox and radio inputs, so
                    the trick of using @readonly to have, well, readonly
                    checkboxes (which still let clicks go through) does not
                    work out of the box. We *still* need to preventDefault()
                    on the event, otherwise the checkbox's state *will* toggle
                    on click
                 */
                e.preventDefault();
            })
            .delegate('td.o_list_record_selector', 'click', function (e) {
                e.stopPropagation();
                var selection = self.get_selection();
                var checked = $(e.currentTarget).find('input').prop('checked');
                $(self).trigger(
                        'selected', [selection.ids, selection.records, ! checked]);
            })
            .delegate('td.o_list_record_delete', 'click', function (e) {
                e.stopPropagation();
                var $row = $(e.target).closest('tr');
                $(self).trigger('deleted', [[self.row_id($row)]]);
                // IE Edge go crazy when we use confirm dialog and remove the focused element
                if(document.hasFocus && !document.hasFocus()) {
                    $('<input />').appendTo('body').focus().remove();
                }
            })
            .delegate('td button', 'click', function (e) {
                e.stopPropagation();
                var $target = $(e.currentTarget),
                      field = $target.closest('td').data('field'),
                       $row = $target.closest('tr'),
                  record_id = self.row_id($row);

                if ($target.attr('disabled')) {
                    return;
                }
                if (self.dataset.model !== "money.transfer") {
                    $target.attr('disabled', 'disabled');
                }
                $(self).trigger('action', [field.toString(), record_id, function (id) {
                    $target.removeAttr('disabled');
                    return self.reload_record(self.records.get(id));
                }]);
            })
            .delegate('a', 'click', function (e) {
                e.stopPropagation();
            })
            .delegate('tr', 'click', function (e) {
                var row_id = self.row_id(e.currentTarget);
                if (row_id) {
                    e.stopPropagation();
                    if (!self.dataset.select_id(row_id)) {
                        throw new Error(_t("Could not find id in dataset"));
                    }
                    self.row_clicked(e);
                }
            });
        },
    })
});