# -*- coding: utf-8 -*-

from odoo import api, fields, models
# from .sale_order_line import REGISTER_TYPE

REGISTER_TYPE = [("register", "Setup"),
                 ("renew", "Renew"),
                 ('capacity', 'Capacity'),
                 ('sale', 'Sale')]


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    register_type = fields.Selection(REGISTER_TYPE, 'Register Type')
    taxes_amount = fields.Float('Taxes Amount', readonly=True, copy=False)
    time = fields.Float('Time', readonly=True)
