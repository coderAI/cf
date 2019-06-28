# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from ast import literal_eval
from odoo.exceptions import Warning


class TransactionConfigSettings(models.TransientModel):
    _name = "transaction.config.settings"
    _inherit = 'res.config.settings'

    journal_ids = fields.Many2many('account.journal', relation='transaction_journal_rel')
    min_amount = fields.Float()
    max_amount = fields.Float()
    keyword_ids = fields.Many2many('transaction.config.settings.keyword', relation='transaction_keyword_rel')

    @api.constrains('min_amount', 'max_amount')
    def check_no(self):
        if self.min_amount and self.min_amount > self.max_amount:
            raise Warning(_("Max amount must be greater than Min amount."))

    @api.multi
    def set_min_amount(self):
        ir_values_obj = self.env['ir.values']
        ir_values_obj.sudo().set_default('transaction.config.settings', 'min_amount', self.min_amount)

    @api.multi
    def get_default_min_amount(self, fields=None):
        return {'min_amount': self.env['ir.values'].get_default('transaction.config.settings', 'min_amount')}

    @api.multi
    def set_max_amount(self):
        ir_values_obj = self.env['ir.values']
        ir_values_obj.sudo().set_default('transaction.config.settings', 'max_amount', self.max_amount)

    @api.multi
    def get_default_max_amount(self, fields=None):
        return {'max_amount': self.env['ir.values'].get_default('transaction.config.settings', 'max_amount')}

    @api.multi
    def set_keyword_ids(self):
        self.env['ir.config_parameter'].set_param('transaction_config.keyword_ids', self.keyword_ids and self.keyword_ids.ids or False)

    @api.multi
    def get_default_keyword_ids(self, fields=None):
        keyword_ids = self.env["ir.config_parameter"].get_param("transaction_config.keyword_ids", default=[])
        if keyword_ids:
            keyword_ids = [int(i) for i in literal_eval(keyword_ids)]
        return {'keyword_ids': keyword_ids and [(6, 0, keyword_ids)] or []}

    @api.multi
    def set_journal_ids(self):
        self.env['ir.config_parameter'].set_param('transaction_config.journal_ids', self.journal_ids and self.journal_ids.ids or False)

    @api.multi
    def get_default_journal_ids(self, fields=None):
        journal_ids = self.env["ir.config_parameter"].get_param("transaction_config.journal_ids", default=[])
        if journal_ids:
            journal_ids = [int(i) for i in literal_eval(journal_ids)]
        return {'journal_ids': journal_ids and [(6, 0, journal_ids)] or []}


class TransactionConfigSettingsKeyword(models.Model):
    _name = "transaction.config.settings.keyword"

    name = fields.Char('Keyword')