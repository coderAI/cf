# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning
from datetime import datetime
from odoo.addons.cf_convert_money.models.convert_money import amount_to_text_vi

class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        team_id = self._context.get('team_id_from_payment', False)
        if team_id:
            user_obj = self.search([('sale_team_id', '=', team_id)])
            user_ids = user_obj and user_obj.ids or []
            if user_ids:
                args += [('id', 'in', user_ids)]
            else:
                args += [('id', 'in', [-1])]
        return super(Users, self).name_search(name, args=args, operator=operator, limit=limit)


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ["account.payment", 'mail.thread']

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    user_id = fields.Many2one('res.users', 'Salesperson', default=lambda self: self.env.user)
    team_id = fields.Many2one('crm.team', 'Sales Team', default=_get_default_team)
    journal_type = fields.Selection(related='journal_id.type')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, store=True)
    bank_transaction_id = fields.Many2one('bank.transaction', string="Payment Transaction", track_visibility='onchange')
    state = fields.Selection(track_visibility='onchange')
    code = fields.Char(string='Code', copy=False, readonly=True, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            if vals.get('payment_type') == 'inbound':
                vals['code'] = self.env['ir.sequence'].next_by_code('account.payment.sale') or 'New'
            elif vals.get('payment_type') == 'outbound':
                vals['code'] = self.env['ir.sequence'].next_by_code('account.payment.purchase') or 'New'
        return super(AccountPayment, self).create(vals)

    @api.multi
    def post(self):
        payment = super(AccountPayment, self).post()
        if self.bank_transaction_id:
            self.bank_transaction_id.write({
                'state': 'done',
                'payment_id': self.id,
            })
        return payment

    @api.onchange('bank_transaction_id')
    def onchange_bank_transaction_id(self):
        self.amount = self.bank_transaction_id and self.bank_transaction_id.amount or 0

    @api.multi
    def cancel(self):
        payment = super(AccountPayment, self).cancel()
        for rec in self:
            if rec.bank_transaction_id:
                rec.bank_transaction_id.state = 'draft'
        return payment

    @api.model
    def format_number(self, number):
        return format(int(number or 0), ',').split('.')[0].replace(',', '.')

    @api.model
    def convert_money_to_string(self, amount):
        return amount and amount_to_text_vi(amount, 'VND') or u'Không đồng'

    @api.model
    def split_date(self, date):
        date = datetime.strptime(date, '%Y-%m-%d')
        return [date.day, date.month, date.year]

    @api.multi
    def print_receipt(self):
        datas = {'ids': self.ids}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'account.payment'
        report_name = 'payment_receipt_template'
        report = self.env['ir.actions.report.xml'].search([('report_name', '=', report_name)])
        if report:
            datas['report_type'] = report[0].report_type
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
        }