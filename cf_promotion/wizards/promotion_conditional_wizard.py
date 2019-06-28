# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning

class PromotionConditionalWizard(models.TransientModel):
    _name = 'promotion.conditional.wizard'

    condition = fields.Selection([('product', 'Product Category'),
                                  ('register_time', 'Register Time'),
                                  ('amount_order', 'Total Amount Sale Order'),
                                  ('amount_product', 'Amount Product Category'),
                                  ('order_type', 'Order Type'),
                                  ('customer_type', 'Customer Type'),
                                  ('list_customer', 'Customers'),
                                  ('customer_email', 'Customer Email'),
                                  # ('customer_level', 'Customer Level'),
                                  ('register_type', 'Register Type'),
                                  ('count_product', 'Total Product'),
                                  ('total_product_discount', 'Total Product Discount')], "Type", default='product')
    product_category_ids = fields.One2many('product.category.wizard', 'wizard_id', string="Product Category")
    promotion_type = fields.Selection([('and', 'All Conditions'), ('or', 'One of the conditions')], default='and')
    register_time_ids = fields.One2many('promotion.conditional.register.time.wizard', 'wizard_id')
    amount_product_ids = fields.One2many('promotion.conditional.amount.product.wizard', 'wizard_id')
    order_type = fields.Many2many('mb.data.type', string="Order Type", domain=[('type', '=', 'order_type')])
    customer_type = fields.Many2many('mb.data.type', string="Customer Type", domain=[('type', '=', 'customer')])
    customer_ids = fields.One2many('promotion.customer.wizard', 'wizard_id', string="Customers")
    customer_email = fields.One2many('promotion.customer.email.wizard', 'wizard_id', string="Customer Email")
    customer_level = fields.Many2many('mb.data.type', string="Customer Level", domain=[('type', '=', 'customer_level')])
    register_type = fields.Many2many('mb.data.type', string="Register Type", domain=[('type', '=', 'register')])
    journal_ids = fields.Many2many('account.journal', string="Journals")
    period_amount = fields.Float("Greater Than")
    total_product = fields.Integer("Total Product")
    point = fields.Integer("Add Point")
    total_product_discount = fields.One2many('promotion.total.product.discount.wizard', 'wizard_id')

    @api.multi
    def action_save(self):
        promotion_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        if self.condition == 'product':
            if not self.product_category_ids:
                raise Warning(_("Pls insert lines"))
            category_ids = self.product_category_ids.mapped('product_category_id') - promotion_id.promotion_product_category
            promotion_id.write({
                'is_product_category': True,
                'product_category_type': self.promotion_type,
                'promotion_product_category': [(4, categ.id) for categ in category_ids]
            })
        elif self.condition == 'register_time':
            if not self.register_time_ids:
                raise Warning(_("Pls insert Product Category"))
            if promotion_id.promotion_register_time:
                # category_ids = promotion_id.promotion_register_time.mapped('product_category_id')
                for line in promotion_id.promotion_register_time:
                    if line.product_category_id in self.register_time_ids.mapped('product_category_id'):
                        line.unlink()
            promotion_id.write({
                'is_register_time': True,
                'register_time_type': self.promotion_type,
                'promotion_register_time': [(0, 0, {
                    'product_category_id': line.product_category_id.id,
                    'month_from': line.month_from,
                }) for line in self.register_time_ids]
            })
        elif self.condition == 'amount_order':
            if self.period_amount <= 0:
                raise Warning(_("Period Total Amount Sale Order must be greater than 0"))
            promotion_id.write({
                'is_amount_order': True,
                'period_total_amount_order': self.period_amount
            })
        elif self.condition == 'amount_product':
            if not self.amount_product_ids:
                raise Warning(_("Pls insert lines"))
            promotion_id.write({
                'is_amount_product': True,
                'amount_product_type': self.promotion_type,
                'promotion_amount_product': [(0, 0, {
                    'product_category_id': line.product_category_id.id,
                    'amount': line.amount,
                }) for line in self.amount_product_ids]
            })
        elif self.condition == 'customer_type':
            if not self.customer_type:
                raise Warning(_("Pls choose Customer Type"))
            promotion_id.write({
                'is_customer_type': True,
                'customer_type': [(4, line.id) for line in self.customer_type]
            })
        elif self.condition == 'order_type':
            if not self.order_type:
                raise Warning(_("Pls choose Order Type"))
            promotion_id.write({
                'is_order_type': True,
                'order_type': [(4, line.id) for line in self.order_type]
            })
        elif self.condition == 'list_customer':
            if not self.customer_ids:
                raise Warning(_("Pls choose Customers"))
            promotion_id.write({
                'is_list_customer': True,
                'customer_ids': [(4, line.id) for line in self.customer_ids.mapped('customer_id')]
            })
        elif self.condition == 'customer_email':
            if not self.customer_email:
                raise Warning(_("Pls input Customer Email"))
            promotion_id.write({
                'is_customer_email': True,
                'customer_email': [(0, 0, {
                    'promotion_id': self.env[self._context.get('active_model')].browse(self._context.get('active_id')).id,
                    'email': email
                }) for email in self.customer_email.mapped('email')]
            })
        # elif self.condition == 'customer_level':
        #     if not self.customer_level:
        #         raise Warning(_("Pls choose Customer Level"))
        #     promotion_id.write({
        #         'is_customer_level': True,
        #         'customer_level': [(4, line.id) for line in self.customer_level]
        #     })
        elif self.condition == 'register_type':
            if not self.register_type:
                raise Warning(_("Pls choose Customer Type"))
            promotion_id.write({
                'is_register_type': True,
                'register_type': [(4, line.id) for line in self.register_type]
            })
        elif self.condition == 'count_product':
            if self.total_product <= 0:
                raise Warning(_("Total Product must be greater than 0"))
            promotion_id.write({
                'is_count_product': True,
                'count_product': self.total_product
            })
        elif self.condition == 'total_product_discount':
            if not self.total_product_discount:
                raise Warning(_("Total Product Discount must be greater than 0"))
            promotion_id.write({
                'is_count_product': True,
                'count_product': self.total_product
            })
        # else:
        #     if not self.journal_ids:
        #         raise Warning(_("Pls choose Journals"))
        #     promotion_id.write({
        #         'is_journal': True,
        #         'journal_type': self.promotion_type,
        #         'journal_ids': [(4, line.id) for line in self.journal_ids]
        #     })
        if self._context.get('nothing'):
            return {
                'type': 'ir.actions.do_nothing',
            }


class PromotionConditionalRegisterTimeWizard(models.TransientModel):
    _name = 'promotion.conditional.register.time.wizard'

    wizard_id = fields.Many2one('promotion.conditional.wizard')
    product_category_id = fields.Many2one('product.category', string="Product Category")
    month_from = fields.Integer("Time")
    # month_to = fields.Integer("Month (To)")
    uom_id = fields.Many2one('product.uom', "UOM", related='product_category_id.uom_id', readonly=True)


class PromotionConditionalAmountProductWizard(models.TransientModel):
    _name = 'promotion.conditional.amount.product.wizard'

    wizard_id = fields.Many2one('promotion.conditional.wizard')
    product_category_id = fields.Many2one('product.category', string="Product Category")
    amount = fields.Float()


class PromotionCategoryWizard(models.TransientModel):
    _name = 'product.category.wizard'

    wizard_id = fields.Many2one('promotion.conditional.wizard')
    product_category_id = fields.Many2one('product.category', "Product Category")


class PromotionCustomerWizard(models.TransientModel):
    _name = 'promotion.customer.wizard'

    wizard_id = fields.Many2one('promotion.conditional.wizard')
    customer_id = fields.Many2one('res.partner', "Customer")


class PromotionCustomerEmailWizard(models.TransientModel):
    _name = 'promotion.customer.email.wizard'

    wizard_id = fields.Many2one('promotion.conditional.wizard')
    email = fields.Char()


class PromotionTotalProductDiscountWizard(models.TransientModel):
    _name = 'promotion.total.product.discount.wizard'

    wizard_id = fields.Many2one('promotion.conditional.wizard')
    product_category_id = fields.Many2one('product.category', string="Product Category")
    total = fields.Integer()


