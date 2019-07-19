# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from lxml import etree
from odoo.osv.orm import setup_modifiers
import logging

_logger = logging.getLogger(__name__)

class mb_e_invoice_wizard(models.TransientModel):
    _name = 'mb.e.invoice.wizard'

    customer_id = fields.Many2one('res.partner',string='Customer')
    invoice_id = fields.Many2one('account.invoice', string='Invoice')
    address = fields.Char(string='Address')
    buyer_name = fields.Char(string='Buyer Name')
    tax_code = fields.Char(string='Tax Code')
    note = fields.Char(string='Note')
    require_date = fields.Date('Require Date')
    payment_type = fields.Selection([('candb', 'Cash and Bank')],
                                    string='Payment Type', default='candb')

    @api.model
    def default_get(self, fields):
        rec_context = dict(self.env.context)
        res = super(mb_e_invoice_wizard, self).default_get(fields)
        if rec_context:
            invoice_id = rec_context.get('invoice_id')
            customer_id = rec_context.get('customer_id')
            customer = self.env['res.partner'].search([('id', '=', customer_id)])

            address = (customer.street or '') + ', ' + (
                    customer.state_id and customer.state_id.name or '') + ', ' + (
                              customer.country_id and customer.country_id.name or '')
            res['customer_id'] = customer_id
            res['invoice_id'] = invoice_id
            res['address'] = address
            res['buyer_name'] = ''
            res['tax_code'] = customer.vat,
        return res


    @api.multi
    def save_btn(self):
        rec_context = dict(self.env.context)
        invoice_id = rec_context.get('invoice_id')
        customer_id = rec_context.get('customer_id')
        invoice_line_ids = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id)]).ids
        rec_context = dict(self.env.context)
        if rec_context:
            mb_e_invoices_obj = self.env['mb.e.invoices']

            if rec_context.get('action_by') == 'create_e_invoice':
                vals={
                    'customer_id': customer_id,
                    #'tax_code': self.tax_code,
                    'payment_type': self.payment_type,
                    'buyer_name': self.buyer_name or '',
                    'require_date': self.require_date,
                    'address': self.address,
                    'invoice_ids': [[6, False, [invoice_id]]],
                    'invoice_line_ids':invoice_line_ids,
                    'note':self.note,
                }
                context = dict(self._context)

                mb_e_invoices_obj.with_context(context).create(vals)
            elif rec_context.get('action_by') == 'set_to_draft':

                mb_e_invoices_data = mb_e_invoices_obj.search([('id','=',rec_context.get('mb_e_invoices_id'))])
                vals = {
                    'customer_id': customer_id,
                    #'tax_code': self.tax_code,
                    'payment_type': self.payment_type,
                    'buyer_name': self.buyer_name or '',
                    'require_date': self.require_date,
                    'address': self.address,
                    'invoice_ids': [[6, False, [invoice_id]]],
                    'invoice_line_ids': invoice_line_ids,
                    'note': self.note,
                    'stages_id': mb_e_invoices_data.change_stages('open')
                }
                mb_e_invoices_data.write(vals)
