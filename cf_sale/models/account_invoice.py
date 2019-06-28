# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
from odoo.addons.cf_convert_money.models.convert_money import amount_to_text_vi
from lxml import etree
from odoo.osv.orm import setup_modifiers


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    vat_status = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('cancel', 'Cancelled')],
                                  "VAT Status", track_visibility='onchange')
    vat_date = fields.Date("VAT Date", track_visibility='onchange')
    vat_no = fields.Char("VAT No.", track_visibility='onchange')
    user_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange',
                              readonly=True, states={'draft': [('readonly', False)],
                                                     'open': [('readonly', False)],
                                                     'paid': [('readonly', False)]},
                              default=lambda self: self.env.user)

    @api.multi
    def write(self, vals):
        if 'state' in vals:
            if vals.get('state') == 'open' and (len(self) == 1 and self.type in ('out_invoice', 'out_refund')) \
                    and not self._context.get('from_po'):
                sale_ids = self.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
                if sale_ids:
                    for order in sale_ids.filtered(lambda so: so.state not in ('paid', 'done')):
                        if order.billing_type == 'prepaid':
                            order.write({
                                'fully_paid': True,
                            })
            if vals.get('state') == 'paid' and (len(self) == 1 and self.type in ('out_invoice', 'out_refund')) \
                    and not self._context.get('from_po'):
                vals['date_invoice'] = datetime.now().date()
                sale_ids = self.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
                if sale_ids:
                    for order in sale_ids.filtered(lambda so: so.state != 'paid'):
                        # if order.billing_type == 'prepaid':
                        order.write({
                            'state': 'paid',
                            'date_order': datetime.now(),
                        })
        return super(AccountInvoice, self).write(vals)

    @api.multi
    def format_number_amount(self):
        return format(int(self.amount_total or 0), ',').split('.')[0].replace(',', '.') + u' VNĐ'

    @api.multi
    def format_number_line(self, line):
        return format(int(line.price_subtotal +
                          line.price_subtotal * (line.invoice_line_tax_ids
                                                 and sum(tax.amount for tax in line.invoice_line_tax_ids)
                                                 or 0) / 100), ',').split('.')[0].replace(',', '.')

    @api.model
    def format_date(self, date, type='%Y-%m-%d', format='%d/%m/%Y'):
        return datetime.strptime(date, type).strftime(format)

    @api.multi
    def convert_money_to_string(self):
        return amount_to_text_vi(self.amount_total, 'VND') or u'Không đồng'

    @api.multi
    def print_bill(self):
        datas = {'ids': self.ids}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'account.invoice'
        report_name = 'vendor_bill_template'
        report = self.env['ir.actions.report.xml'].search([('report_name', '=', report_name)])
        if report:
            datas['report_type'] = report[0].report_type
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
        }

    @api.multi
    def get_index_line(self, line):
        for index, item in enumerate(self.invoice_line_ids):
            if item == line:
                return index + 1
            
    @api.multi
    def action_invoice_cancel(self):
        for invoice in self:
            order_id = self.env['sale.order'].search([('name', '=', invoice.origin)])
            if order_id:
                if any(line.service_status in ('waiting', 'done') for line in order_id.order_line):
                    raise UserError(_("Service have send request active, can't cancel invoice"))
                order_id.state = 'sale'
        return super(AccountInvoice, self).action_invoice_cancel()

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountInvoice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                       submenu=submenu)
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            if self.user_has_groups('account.group_account_invoice'):
                field_user_id = doc.xpath("//field[@name='user_id']")
                fields_to_options = doc.xpath("//field")
                for node in fields_to_options:
                    if field_user_id and node in (field_user_id[0]):
                        node.set('attrs', "{'readonly': [('state', 'not in', ('draft', 'open', 'paid'))]}")
                        setup_modifiers(node)
        res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def action_invoice_open(self):
        rsl = super(AccountInvoice, self).action_invoice_open()
        for invoice in self:
            order_id = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
            if not order_id.picking_ids:
                order_id.order_line._action_procurement_create()
        return rsl