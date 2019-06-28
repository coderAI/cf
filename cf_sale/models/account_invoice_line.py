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

    @api.model
    def get_account_id(self, product, invoice_type, register_type):
        if not product:
            return False
        # order_line = self.sale_line_ids
        if invoice_type in ['out_invoice', 'out_refund']:
            if register_type == 'capacity':
                account_id = product.categ_id.capacity_account_income_id.id or False
            elif register_type in ('register', 'sale'):
                account_id = product.categ_id.register_account_income_id.id or False
            else:
                account_id = product.categ_id.renew_account_income_id.id or False
        else:
            if register_type == 'capacity':
                account_id = product.categ_id.capacity_account_expense_id.id or False
            elif register_type in ('register', 'sale'):
                account_id = product.categ_id.register_account_expense_id.id or False
            else:
                account_id = product.categ_id.renew_account_expense_id.id or False
        return account_id

    @api.model
    def get_account_analytic_id(self, product, invoice_type, register_type):
        # order_line = self.sale_line_ids
        if invoice_type in ['out_invoice', 'out_refund']:
            if register_type == 'capacity':
                acc_analytic_id = product.categ_id.capacity_analytic_income_account_id.id or False
            elif register_type in ('register', 'sale'):
                acc_analytic_id = product.categ_id.register_analytic_income_acc_id.id or False
            else:
                acc_analytic_id = product.categ_id.renew_analytic_income_account_id.id or False
        else:
            if register_type == 'capacity':
                acc_analytic_id = product.categ_id.capacity_analytic_expense_acc_id.id or False
            elif register_type in ('register', 'sale'):
                acc_analytic_id = product.categ_id.register_analytic_expense_acc_id.id or False
            else:
                acc_analytic_id = product.categ_id.renew_analytic_expense_acc_id.id or False
        return acc_analytic_id

    @api.multi
    def write(self, vals):
        """
        TO DO:
            - Update account and account analytic for invoice
        """
        res = super(AccountInvoiceLine, self).write(vals)

        if vals.get('product_id') or vals.get('register_type'):
            new_product_id = vals.get('product_id', False)
            if new_product_id:
                new_product_id = self.env['product.product'].browse(
                    new_product_id)
            new_register_type = vals.get('register_type', False)

            for line in self:
                invoice = self.env['account.invoice'].browse(
                    line.invoice_id.id)
                account_id = self.get_account_id(
                    new_product_id or line.product_id,
                    invoice.type, new_register_type or line.register_type)
                analytic_account = self.get_account_analytic_id(
                    new_product_id or line.product_id,
                    invoice.type, new_register_type or line.register_type)
                if account_id:
                    line.account_id = account_id
                if analytic_account:
                    line.account_analytic_id = analytic_account
        return res

    @api.model
    def create(self, vals):
        """
        TO DO:
        - Update account and account analytic for invoice
        """
        if vals.get('product_id') and vals.get('invoice_id') and \
                vals.get('register_type'):
            invoice = self.env['account.invoice'].browse(vals['invoice_id'])
            product = self.env['product.product'].browse(vals['product_id'])
            register_type = vals['register_type']
            # if not vals.get('invoice_line_tax_ids'):
            #     tax = False
            # else:
            #     tax = self.env['account.tax'].browse(
            #         vals['invoice_line_tax_ids'][0][2])
            account_id = self.get_account_id(
                product, invoice.type, register_type)
            if account_id:
                vals.update({'account_id': type(account_id).__name__ == 'int' and account_id or account_id.id})
            analytic_account = self.get_account_analytic_id(
                product, invoice.type, register_type)
            if analytic_account:
                vals.update({'account_analytic_id': analytic_account})
        return super(AccountInvoiceLine, self).create(vals)
