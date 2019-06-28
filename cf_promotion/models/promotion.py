# -*- coding: utf-8 -*-
from odoo import api, fields, models
# import time
# from datetime import datetime, timedelta
# from dateutil import relativedelta
# import logging as _logger

class MBPromotion(models.Model):
    _name = "mb.promotion"
    _inherit = 'mail.thread'

    name = fields.Char("Promotion Name", track_visibility='onchange')
    date_from = fields.Datetime("Date From", track_visibility='onchange')
    date_to = fields.Datetime("Date To", track_visibility='onchange')
    type = fields.Selection([('and', 'All Conditions'), ('or', 'One of the conditions')],
                            "Condition Type", default='and', track_visibility='onchange')
    only_used_once = fields.Boolean("A Customer only used once", track_visibility='onchange')
    status = fields.Selection([('run', 'Running'), ('stop', 'Stopped')], "Status",
                              default='run', track_visibility='onchange')
    coupon_ids = fields.One2many('mb.coupon', 'promotion_id', "Promotion Coupon")
    coupon_count = fields.Integer(compute="compute_coupon")
    # Product Category
    is_product_category = fields.Boolean()
    product_category_type = fields.Selection([('and', 'All Conditions'), ('or', 'One of the conditions')],
                                             "Product Category Option", default='and')
    promotion_product_category = fields.Many2many('product.category', 'promotion_product_category',
                                                  'promotion_id', 'product_category_id', "Product Category")
    # Register Time
    is_register_time = fields.Boolean()
    register_time_type = fields.Selection([('and', 'All Conditions'), ('or', 'One of the conditions')],
                                          "Register Time Option", default='and')
    promotion_register_time = fields.One2many('promotion.register.time', 'promotion_id', "Register Time")
    # Total Amount Order
    is_amount_order = fields.Boolean()
    period_total_amount_order = fields.Float("Period Total Amount Sale Order")
    # Amount Product Category
    is_amount_product = fields.Boolean()
    amount_product_type = fields.Selection([('and', 'All Conditions'), ('or', 'One of the conditions')],
                                           "Amount Product Option", default='and')
    promotion_amount_product = fields.One2many('promotion.amount.product', 'promotion_id', "Total Amount Product")
    # Order Type
    is_order_type = fields.Boolean()
    order_type = fields.Many2many('mb.data.type', 'promotion_order_type',
                                  'promotion_id', 'order_type_id', "Order Type")
    # Customer Type
    is_customer_type = fields.Boolean()
    customer_type = fields.Many2many('mb.data.type', 'promotion_customer_type',
                                     'promotion_id', 'customer_type_id', "Customer Type")
    # List Customer
    is_list_customer = fields.Boolean()
    customer_ids = fields.Many2many('res.partner', 'promotion_customers',
                                     'promotion_id', 'customer_id', "Customers")
    # Customer Email
    is_customer_email = fields.Boolean()
    customer_email = fields.One2many('promotion.customer.email', 'promotion_id', "Customer Email")
    # Register Type
    is_register_type = fields.Boolean()
    register_type = fields.Many2many('mb.data.type', 'promotion_register_type',
                                     'promotion_id', 'register_type_id', "Register Type")
    # Count Product
    is_count_product = fields.Boolean()
    count_product = fields.Integer("Total Product")
    # Total Product Discount
    is_total_product_discount = fields.Boolean("Limit Product")
    total_product_discount = fields.One2many('promotion.total.product.discount', 'promotion_id',
                                             "Total Product Discount")
    # Discount Money
    is_discount_money = fields.Boolean("Discount Total Amount Product")
    promotion_discount_money = fields.One2many('promotion.discount.money', 'promotion_id', 'Amount Discount')
    # Discount Percent
    is_discount_percent = fields.Boolean("Discount Total Percent Product")
    promotion_discount_percent = fields.One2many('promotion.discount.percent', 'promotion_id', 'Percent Discount')
    # Discount Used Time
    is_discount_used_time = fields.Boolean("Bonus Used Time")
    discount_used_time = fields.One2many('promotion.discount.used.time', 'promotion_id', "Register Time",
                                                 domain=[('type', '=', 'used_time')])
    # Discount Product
    is_discount_product = fields.Boolean("Product Free")
    promotion_discount_product = fields.One2many('promotion.discount.used.time', 'promotion_id', "Product Free",
                                                 domain=[('type', '=', 'product_free')])
    # Discount Point
    is_discount_point = fields.Boolean("Add Point")
    discount_point = fields.Float("Add Point")

    def compute_coupon(self):
        for pr in self:
            # print pr.coupon_ids
            pr.coupon_count = len(pr.coupon_ids)

    @api.multi
    def action_stop(self):
        self.write({'status': 'stop'})

    @api.multi
    def action_start(self):
        self.write({'status': 'run'})

    @api.onchange('promotion_product_category', 'promotion_register_time', 'period_total_amount_order',
                  'promotion_amount_product', 'customer_type', 'register_type', 'count_product',
                  'customer_ids', 'customer_email')
    def onchange_condition(self):
        if not self.promotion_product_category:
            self.is_product_category = False
        if not self.promotion_register_time:
            self.is_register_time = False
        if self.period_total_amount_order <= 0:
            self.is_amount_order = False
        if not self.promotion_amount_product:
            self.is_amount_product = False
        if not self.customer_type:
            self.is_customer_type = False
        if not self.customer_ids:
            self.is_list_customer = False
        if not self.customer_email:
            self.is_customer_email = False
        if not self.register_type:
            self.is_register_type = False
        if self.count_product <= 0:
            self.is_count_product = False

    @api.multi
    def open_coupon_action(self):
        return {
            'name': 'Promotion',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mb.promotion',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'self',
        }

    @api.multi
    def open_sale_order_action(self):
        return {
            'name': 'Sale Orders',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'domain': [('coupon', 'in', self.coupon_ids.mapped('name'))],
            'target': 'self',
        }


class PromotionRegisterTime(models.Model):
    _name = 'promotion.register.time'

    promotion_id = fields.Many2one('mb.promotion', "Promotion")
    product_category_id = fields.Many2one('product.category', "Product Category")
    month_from = fields.Float("Time")
    # month_to = fields.Float("Time (To)")
    uom_id = fields.Many2one('product.uom', "UOM", related='product_category_id.uom_id', readonly=True)


class PromotionAmountProduct(models.Model):
    _name = 'promotion.amount.product'

    promotion_id = fields.Many2one('mb.promotion', "Promotion")
    product_category_id = fields.Many2one('product.category', "Product Category")
    amount = fields.Float("Amount Greater Than")


class PromotionCustomerEmail(models.Model):
    _name = 'promotion.customer.email'

    promotion_id = fields.Many2one('mb.promotion', "Promotion")
    email = fields.Char()


class PromotionDiscountMoney(models.Model):
    _name = 'promotion.discount.money'

    promotion_id = fields.Many2one('mb.promotion', "Promotion")
    product_category_id = fields.Many2one('product.category', "Product Category")
    setup_amount = fields.Float("Setup Amount Discount")
    renew_amount = fields.Float("Renew Amount Discount")


class PromotionDiscountPercent(models.Model):
    _name = 'promotion.discount.percent'

    promotion_id = fields.Many2one('mb.promotion', "Promotion")
    product_category_id = fields.Many2one('product.category', "Product Category")
    setup_percent = fields.Float("Setup Percent Discount")
    renew_percent = fields.Float("Renew Percent Discount")


class PromotionDiscountUsedTime(models.Model):
    _name = 'promotion.discount.used.time'

    promotion_id = fields.Many2one('mb.promotion', "Promotion")
    product_category_id = fields.Many2one('product.category', "Product Category")
    time = fields.Integer()
    uom_id = fields.Many2one('product.uom', related='product_category_id.uom_id', string="UOM", readonly=True)
    type = fields.Selection([('used_time', "Used Time"), ('product_free', "Product Free")], "Type")
    percent = fields.Float("Discount Percent (%)", default=100)


class PromotionTotalProductDiscount(models.Model):
    _name = 'promotion.total.product.discount'

    promotion_id = fields.Many2one('mb.promotion', "Promotion")
    product_category_id = fields.Many2one('product.category', "Product Category")
    total = fields.Integer()

# class PromotionCoupon(models.Model):
#     _name = 'promotion.coupon'
#
#     promotion_id = fields.Many2one('mb.promotion', "Promotion")
#     code = fields.Char("Promotion Code")
#     expired_date = fields.Datetime("Expired Date")
#     max_use_times = fields.Integer('Max Use Times')
#     used_date = fields.Datetime("Used Date")
#     used_times = fields.Integer("Used Times")
#     status = fields.Selection([('new', 'New'), ('stop', 'Stopped'), ('used', 'Used')], "Status")