# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # type = fields.Selection(selection_add=[('upgrade', 'Upgrade')])
    is_upgrade = fields.Boolean("Is Upgrade", compute="check_is_upgrade",
                                help="If SO have service to upgrade, return True, else return False")

    @api.depends('order_line', 'order_line.register_type')
    def check_is_upgrade(self):
        for order in self:
            order.is_upgrade = False
            if any(line.register_type == 'upgrade' for line in order.order_line):
                order.is_upgrade = True

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        invoice_ids = super(SaleOrder, self).action_invoice_create(grouped=grouped, final=final)
        invoices = self.env['account.invoice'].browse(invoice_ids)
        for inv in invoices.filtered(lambda i: i.state == 'draft'):
            # for line in inv.invoice_line_ids.filtered(lambda l: l.sale_line_ids.register_type == 'upgrade' and
            #                                                     l.register_type == 'renew'):
            # line_ids = inv.invoice_line_ids.filtered(
            #         lambda l: l.product_id in l.sale_line_ids.order_id.order_line.filtered(
            #                 lambda ol: ol.register_type == 'upgrade').mapped(
            #                 'product_id') and l.register_type == 'renew')
            # inv_line_ids = self.env['account.invoice.line']
            # for inv_line in inv.invoice_line_ids:
            #     order_line = inv_line.invoice_id.invoice_line_ids.mapped('sale_line_ids').mapped('order_id').mapped('order_line').filtered(lambda l: l.register_type == 'upgrade')
            #     product_ids = order_line.mapped('product_id')
            #     if inv_line.product_id in product_ids and inv_line.register_type == 'renew':
            #         inv_line_ids |= inv_line
            for line in inv.invoice_line_ids.filtered(
                        lambda l: l.product_id in l.invoice_id.invoice_line_ids.mapped('sale_line_ids').mapped(
                                'order_id').mapped('order_line').filtered(
                                lambda ol: ol.register_type == 'upgrade').mapped(
                                'product_id')):
                if line.register_type == 'renew':
                    if not line.invoice_line_tax_ids:
                        continue
                    if line.mapped('sale_line_ids') and line.mapped('sale_line_ids')[0].refund_amount <= 0:
                        continue
                    other_lines = inv.invoice_line_ids.filtered(lambda l: l.register_type == 'renew' and
                                                                          l.price_unit < 0)
                    if not other_lines or line.product_id not in other_lines.mapped('product_id'):
                        order_line = line.mapped('sale_line_ids')
                        if not order_line:
                            order_line = line.invoice_id.invoice_line_ids.mapped('sale_line_ids').filtered(
                                lambda l: l.register_type == 'upgrade' and l.product_id == line.product_id)
                        # line.price_unit = order_line.price_new_category + order_line.up_price
                        line.write({
                            'price_unit': order_line.renew_price + order_line.up_price + order_line.refund_amount,
                            'product_category_id': order_line.product_category_id and
                                                   order_line.product_category_id.id or False,
                            'account_id': order_line.product_category_id.renew_account_income_id and
                                          order_line.product_category_id.renew_account_income_id.id,
                            'account_analytic_id': order_line.product_category_id.renew_analytic_income_account_id and
                                                   order_line.product_category_id.renew_analytic_income_account_id.id
                        })
                        new_line = self.env['account.invoice.line'].create({
                            'invoice_id': inv.id,
                            'register_type': 'renew',
                            'product_id': line.product_id and line.product_id.id,
                            # 'product_category_id': order_line.old_category_id and order_line.old_category_id.id,
                            'product_category_id': order_line.product_id and order_line.product_id.categ_id and
                                                   order_line.product_id.categ_id.id or False,
                            'quantity': 1,
                            'time': 1,
                            'price_unit': order_line.refund_amount * -1,
                            'name': line.product_id and line.product_id.partner_ref or '',
                            'account_id': order_line.product_id.categ_id.renew_account_income_id
                                          and order_line.product_id.categ_id.renew_account_income_id.id,
                            'invoice_line_tax_ids': order_line.tax_id and [(6, 0, [order_line.tax_id.id])] or [],
                            'account_analytic_id': order_line.product_id.categ_id.renew_analytic_income_account_id and
                                                   order_line.product_id.categ_id.renew_analytic_income_account_id.id,
                            'company_id': inv.company_id.id
                        })
                        new_line.write({
                            'account_id': order_line.product_id.categ_id.renew_account_income_id and
                                          order_line.product_id.categ_id.renew_account_income_id.id,
                            'account_analytic_id': order_line.product_id.categ_id.renew_analytic_income_account_id and
                                                   order_line.product_id.categ_id.renew_analytic_income_account_id.id
                        })
                elif line.register_type == 'register':
                    order_line = line.mapped('sale_line_ids')
                    if not order_line:
                        order_line = line.invoice_id.invoice_line_ids.mapped('sale_line_ids').filtered(
                            lambda l: l.register_type == 'upgrade' and l.product_id == line.product_id)
                    line.write({
                        'product_category_id': order_line.product_category_id and
                                               order_line.product_category_id.id or False,
                        'account_id': order_line.product_category_id.register_account_income_id and
                                      order_line.product_category_id.register_account_income_id.id,
                        'account_analytic_id': order_line.product_category_id.register_analytic_income_acc_id and
                                               order_line.product_category_id.register_analytic_income_acc_id.id
                    })
        return invoice_ids


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_new_category = fields.Float("Price New Category (Untaxed)")
    refund_amount = fields.Float("Refund Amount (Untaxed)")
    old_category_id = fields.Many2one('product.category', string='Old Category')

    @api.multi
    def activate(self):
        if self.register_type == 'upgrade':
            self.product_id.write({'categ_id': self.product_category_id.id})
            service_id = self.env['sale.service'].search([('product_id', '=', self.product_id.id)])
            service_id.write({'product_category_id': self.product_category_id.id})
        return super(SaleOrderLine, self).activate()
