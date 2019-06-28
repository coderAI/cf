# -*- coding: utf-8 -*-
from ast import literal_eval
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import Warning
import logging

class MoneyTransfer(models.Model):
    _name = 'money.transfer'
    _order = "date DESC"
    _inherit = ['mail.thread']

    journal_id = fields.Many2one('account.journal', 'Journal', track_visibility='onchange')
    journal_number = fields.Char(track_visibility='onchange')
    code = fields.Char(track_visibility='onchange')
    date = fields.Datetime(track_visibility='onchange')
    amount = fields.Float(default=0.0, track_visibility='onchange')
    description = fields.Char(track_visibility='onchange')
    transaction_id = fields.Many2one('bank.transaction', 'Transaction')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', track_visibility='onchange')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('transfer_uniq', 'unique(journal_id, code)', _("Journal and Code must be unique!")),
    ]

    @api.model
    def create(self, vals):
        if not vals.get('code', ''):
            vals['code'] = self.env['ir.sequence'].next_by_code('bank.transaction') or ''
        return super(MoneyTransfer, self).create(vals)

    def name_get(self):
        res = []
        for record in self:
            name = record.journal_number or ''
            if record.code:
                name = '%s' % record.code
            res.append((record.id, name))
        return res

    @api.model
    def add_money_transfer(self, values={}):
        if not values:
            return _("Data input is empty!")
        journal_obj = self.env['account.journal']
        company_obj = self.env['res.company']
        data = {'amount': values['amount']}
        if values.get('company_id'):
            if not company_obj.browse(values['company_id']):
                return {'"code"': 0, '"msg"': '"Company ID is not correct"'}
            else:
                data['company_id'] = values['company_id']
                company_id = values['company_id']
        else:
            return {'"code"': 0, '"msg"': '"Company ID is not exist"'}

        if values.get('journal_code'):
            journal = journal_obj.search([
                ('name', '=', values['journal_code']),
                ('type', 'in', ['cash', 'bank']),
                ('company_id', '=', company_id),
            ])
            if not journal:
                return {'"code"': 0, '"msg"': '"Journal code is not correct"'}
            elif len(journal) > 1:
                return {'"code"': 0, '"msg"': '"Too many Journal"'}
            else:
                if journal.company_id.id != values.get('company_id'):
                    return {'"code"': 0, '"msg"': '"Journal not belong company."'}
                data['journal_id'] = journal.id
        else:
            return {'"code"': 0, '"msg"': '"Journal code is not exist"'}

        if values.get('journal_number'):
            data['journal_number'] = values['journal_number']

        if values.get('code'):
            data['code'] = values['code']
        else:
            return {'"code"': 0, '"msg"': '"Code number is not exist"'}

        if values.get('date'):
            data['date'] = values['date']
        else:
            return {'"code"': 0, '"msg"': '"Date of transaction is not exist"'}
        if values.get('description'):
            data['description'] = values['description']
        else:
            return {'"code"': 0, '"msg"': '"Description of transaction is not exist"'}

        transfer_id = self.search([('code', '=', data['code']), ('journal_id', '=', data['journal_id'])])
        if transfer_id:
            return {'"code"': 1, '"msg"': '"There is Money transfer with code is {} and journal number is {}"'.format(
                data['code'], data['journal_id']), '"data"': transfer_id.id}
        try:
            transfer_id = self.create(data)
            return {'"code"': 1, '"msg"': '"Creating Money Transfer is Done. ID = {}"'.format(transfer_id.id), '"data"': transfer_id.id}
        except Exception as e:
            self._cr.rollback()
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.multi
    def check_condition(self):
        keyword_obj = self.env['transaction.config.settings.keyword']
        min_amount = self.env['ir.values'].get_default('transaction.config.settings', 'min_amount')
        max_amount = self.env['ir.values'].get_default('transaction.config.settings', 'max_amount')
        journal_ids = self.env["ir.config_parameter"].get_param("transaction_config.journal_ids", default=[])
        keyword_ids = self.env["ir.config_parameter"].get_param("transaction_config.keyword_ids", default=[])
        keywords = keyword_ids and [int(i) for i in literal_eval(keyword_ids)] or False
        journals = journal_ids and [int(i) for i in literal_eval(journal_ids)] or False
        if max_amount and (self.amount > max_amount or self.amount < min_amount):
        # or self.journal_id.id in journals or is_ban_keyword:
            return {'code': 0, 'msg': "Can't transfer with amount %s" % self.amount}
        if journals and self.journal_id.id in journals:
            return {'code': 0, 'msg': "Can't transfer with journal %s" % self.journal_id.name}
        if keywords:
            key_ids = keyword_obj.browse(keywords)
            if any(key.name in self.description for key in key_ids):
                return {'code': 0, 'msg': "Can't transfer with description %s" % (self.description or '')}
        return {'code': 1}

    @api.model
    def get_money_transfer(self):
        transfer = self.search([('state', '=', 'draft'), ('amount', '>', 0)])
        data = []
        try:
            for trans in transfer:
                data.append({
                    '"id"': trans.id,
                })
            return {'"data"': data, '"code"': 1}
        except Exception as e:
            return {'"msg"': '"Error: %s"' % (e.message or repr(e)), '"code"': 1}

    @api.model
    def transfer_to_bank_transaction(self, id):
        if not id:
            return {'"code"': 0, '"msg"': '"Can`t get ID"'}
        transfer = self.browse(id)
        if not transfer or transfer.state != 'draft':
            return {'"code"': 0, '"msg"': '"Transfer is wrong (Not exists or transfer have state != Draft)"'}
        if not transfer.code:
            return {'"code"': 0, '"msg"': '"Can`t get Code"'}
        if not transfer.date:
            return {'"code"': 0, '"msg"': '"Can`t get Date"'}
        if not transfer.description:
            return {'"code"': 0, '"msg"': '"Can`t get Description"'}
        if not transfer.journal_id:
            return {'"code"': 0, '"msg"': '"Can`t get Journal"'}
        if not transfer.company_id:
            return {'"code"': 0, '"msg"': '"Can`t get Company"'}
        if transfer.amount <= 0:
            return {'"code"': 0, '"msg"': '"Can`t get Amount (Amount must be > 0)"'}
        try:
            transfer.add_bank_transaction()
            return {'"code"': 1, '"msg"': '"Successfully"'}
        except Exception as e:
            return {'"code"': 1, '"msg"': '"%s"' % (e.message or repr(e))}

    @api.multi
    def add_bank_transaction(self):
        bank_obj = self.env['bank.transaction']
        if self.state != 'draft':
            raise Warning(_("The record had transferred: %s" % self.state))
        check_condition = self.check_condition()
        if check_condition.get('code') == 0:
            raise Warning(_(check_condition.get('msg')))
        bank_id = bank_obj.create({
            'code': self.code,
            'transaction_date': self.date,
            'description': self.description,
            'journal_id': self.journal_id.id,
            'amount': self.amount,
        })
        self.write({
            'state': 'done',
            'transaction_id': bank_id.id,
        })
