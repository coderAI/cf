# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BankTransaction(models.Model):
    _name = 'bank.transaction'
    _inherit = ['mail.thread']
    _order = "create_date DESC"
    _rec_name = 'code'

    code = fields.Char("Code", required=False, readonly=True, track_visibility='onchange')
    amount = fields.Float("Amount", required=True, track_visibility='onchange')
    journal_id = fields.Many2one('account.journal', string="Payment Method",
                                 required=True, readonly=False, track_visibility='onchange')
    description = fields.Text('Description', track_visibility='onchange')
    payment_id = fields.Many2one('account.payment', 'Payment', readonly=True, track_visibility='onchange')
    account_move_id = fields.Many2one('account.move', 'Journal Entry', track_visibility='onchange')
    write_uid = fields.Many2one('res.users', string='Updated by', readonly=True, track_visibility='onchange')
    transaction_date = fields.Date("Date")
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string="Status",
                             default='draft', track_visibility='onchange')

    @api.multi
    def convert_type(self, total):
        return '{0:,.0f}'.format(int(total)) if total != 0 else 0

    @api.multi
    def name_get(self):
        res = []
        for record in self:
            name = record.code + ' - ' + self.convert_type(record.amount)
            res.append((record.id, name))
        return res