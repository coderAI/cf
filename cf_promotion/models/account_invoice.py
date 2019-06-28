# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
import logging
from odoo.exceptions import Warning

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    # @api.multi
    # def action_invoice_open(self):
    #     for invoice in self:
    #         order_id = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
    #         if order_id.coupon:
    #             coupon_id = self.env['mb.coupon'].search([('name', '=', order_id.coupon.strip())])
    #             if coupon_id:
    #                 count_order = self.env['sale.order'].sudo().search_count([('state', 'in', ('paid', 'done')),
    #                                                                           ('coupon', '=', order_id.coupon.strip())])
    #                 if count_order >= coupon_id.max_used_time:
    #                     raise Warning(_("Coupon used exceeded number of times allowed"))
    #                 if datetime.now().strftime('%Y-%m-%d %H:%M:%S') > coupon_id.expired_date:
    #                     raise Warning(_("Coupon used over expired time"))
    #                 promotion_id = coupon_id.promotion_id
    #                 if promotion_id.status <> 'run':
    #                     raise Warning(_("Promotion have stopped"))
    #                 if promotion_id.date_from > datetime.now().strftime('%Y-%m-%d %H:%M:%S') or \
    #                         datetime.now().strftime('%Y-%m-%d %H:%M:%S') > promotion_id.date_to:
    #                     raise Warning(_("Promotion not yet started"))
    #                 # Check A Customer only used once
    #                 if promotion_id.only_used_once:
    #                     order_ids = self.env['sale.order'].search_count([('partner_id', '=', order_id.partner_id.id),
    #                                                                      ('coupon', '=', order_id.coupon.strip()),
    #                                                                      ('state', 'in', ('paid', 'done')),
    #                                                                      ('state', 'not in', ('cancel',))])
    #
    #                     if order_ids >= 1:
    #                         raise Warning(_("Customer used the coupon code in another order"))
    #                 # Check Total Product Discount
    #                 if promotion_id.is_total_product_discount and len(promotion_id.total_product_discount) > 0:
    #                     for item in promotion_id.total_product_discount:
    #                         category_ids = self.env['product.category'].search(
    #                             [('id', 'child_of', item.product_category_id.id)])
    #                         domain = [('product_category_id', 'in', category_ids.ids),
    #                                   ('order_id.fully_paid', '=', True),
    #                                   ('order_id.coupon', 'in', promotion_id.coupon_ids.mapped('name'))]
    #                         if promotion_id.is_register_type and promotion_id.register_type:
    #                             domain.append(('register_type', 'in', promotion_id.register_type.mapped('code')))
    #                         order_line_ids = self.env['sale.order.line'].search_count(domain)
    #                         order_count_service = order_id.order_line.filtered(lambda l: l.product_category_id in category_ids)
    #                         if promotion_id.is_register_type and promotion_id.register_type:
    #                             order_count_service = order_count_service.filtered(
    #                                 lambda l: l.register_type in promotion_id.register_type.mapped('code'))
    #                         if order_line_ids + len(order_count_service) > item.total:
    #                             raise Warning(
    #                                 _("%s has run out of numbers for registration" % item.product_category_id.name))
    #                 # pass_line = []
    #     return super(AccountInvoice, self).action_invoice_open()