# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from lxml import etree
from odoo.osv.orm import setup_modifiers
import logging

_logger = logging.getLogger(__name__)

class mb_reason_invoice_line_wizard(models.TransientModel):
    _name = 'mb.reason.invoice.line.wizard'
    mb_reason_invoice_id = fields.Many2one('mb.reason.invoice', string='Reason')
    name = fields.Char(related='mb_reason_invoice_id.name', string='Reason', store=True)
    mb_e_invoices_id = fields.Many2one('mb.e.invoices', string='E-Invoice')
    note = fields.Char(string='Note')




    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(mb_reason_invoice_line_wizard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                                         submenu=submenu)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='mb_reason_invoice_id']")
        if dict(self.env.context).get('action_type') == 'set_reject':
            for node in nodes:
                node.set('domain', "[('type', '=', 'e_invoice_reject')]")
            res['arch'] = etree.tostring(doc)
        elif dict(self.env.context).get('action_type') == 'set_cancel':
            for node in nodes:
                node.set('domain', "[('type', '=', 'e_invoice_cancel')]")
            res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def confirm_btn(self):
        rec_context = dict(self.env.context)
        vals={}
        res =False
        if rec_context.get('action_type') == 'set_cancel':
            vals.update({
                            'mb_reason_invoice_id': self.mb_reason_invoice_id.id,
                            'mb_e_invoices_id': rec_context.get('default_res_id'),
                            'note':self.note,
                         })
            self.env['mb.reason.invoice.line'].create(vals)
            mb_e_invoices_ids = self.env['mb.e.invoices'].search([('id', '=', rec_context.get('default_res_id'))])
            self.env['mb.e.invoices'].cancel_order_api_call(mb_e_invoices_ids)

            for record in mb_e_invoices_ids:
                record.write({
                    'stages_id': record.change_stages('cancel')
                })
            res = True
        elif rec_context.get('action_type') == 'set_reject':
            vals.update({
                            'mb_reason_invoice_id': self.mb_reason_invoice_id.id,
                            'mb_e_invoices_id': rec_context.get('default_res_id'),
                            'note':self.note,
                         })
            self.env['mb.reason.invoice.line'].create(vals)
            mb_e_invoices_ids = self.env['mb.e.invoices'].search([('id', '=', rec_context.get('default_res_id'))])
            for record in mb_e_invoices_ids:
                record.write({
                    'stages_id': record.change_stages('refuse')
                })
            res = True
        return res
