# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.addons.cf_sale.models.sale_order import STATES

class SaleOrderWizard(models.TransientModel):
    _name = "sale.order.wizard"
    _description = "Get order line and show on wizard"

    name = fields.Char(string='Order Number')
    state = fields.Selection(STATES, string='Status')
    date_order = fields.Datetime(string='Order Date')
    user_id = fields.Many2one('res.users', string='Salesperson')
    team_id = fields.Many2one('crm.team', string='SalesTeam')
    partner_id = fields.Many2one('res.partner', string='Customer')
    billing_type = fields.Selection([('prepaid', 'Prepaid'), ('postpaid', 'Postpaid')], "Billing Type")
    type = fields.Selection([('normal', 'Normal'), ('renewed', 'Renewed'), ('online', 'Online')], string='Type')

class SearchOrderWizard(models.TransientModel):
    _name = "search.order.wizard"
    _description = "Allows sales users to search all SO"

    def default_search_product(self):
        if self.product_code or self.product_name:
            return True
        return False

    name = fields.Char(string="Order Number")
    customer_code = fields.Char(string="Customer Code")
    customer_name = fields.Char(string="Customer Name")
    product_category = fields.Many2one('product.category', string='Product Category')
    product_code = fields.Char(string='Product Code')
    product_name = fields.Char(string='Product Name')
    order_ids = fields.Many2many("sale.order.wizard")
    is_product = fields.Boolean(string='Is search product', default=lambda self: self.default_search_product())

    @api.onchange('product_code', 'product_name')
    def check_search_product(self):
        self.is_product = False
        if self.product_code or self.product_name:
            self.is_product = True

    @api.multi
    def search_order(self):
        self.ensure_one()
        self.order_ids = False
        args = []
        args_line = []
        orders = False
        order_ids = False
        if self.name:
            args += [('name', '=', self.name)]
        if self.customer_code:
            customer_id = self.env['res.partner'].search([('ref', '=', self.customer_code)])
            args += [('partner_id', '=', customer_id.id)]
        if self.customer_name:
            customer_ids = self.env['res.partner'].search([('name', '=', self.customer_name), ('customer', '=', True)])
            args += [('partner_id', 'in', customer_ids.ids)]
        if args:
            orders = self.env['sale.order'].sudo().search(args)
        if self.product_category:
            products = self.env['product.product'].search([('categ_id', '=', self.product_category.id)])
            args_line += [('product_id', 'in', products.ids)]
        if self.product_code:
            products = self.env['product.product'].search([('default_code', '=', self.product_code)])
            args_line += [('product_id', 'in', products.ids)]
        if self.product_name:
            products = self.env['product.product'].search([('name', '=', self.product_name)])
            args_line += [('product_id', 'in', products.ids)]
        if args_line:
            order_ids = self.env['sale.order.line'].sudo().search(args_line).mapped('order_id')
        if orders or order_ids:
            if not args and args_line:
                self.order_ids = [(0, 0, {'name': order.name,
                                          'state': order.state,
                                          'date_order': order.date_order,
                                          'user_id': order.user_id.id,
                                          'team_id': order.team_id.id,
                                          'billing_type': order.billing_type,
                                          'type': order.type,
                                          'partner_id': order.partner_id.id}) for order in order_ids]
            elif args and not args_line:
                self.order_ids = [(0, 0, {'name': order.name,
                                          'state': order.state,
                                          'date_order': order.date_order,
                                          'user_id': order.user_id.id,
                                          'team_id': order.team_id.id,
                                          'billing_type': order.billing_type,
                                          'type': order.type,
                                          'partner_id': order.partner_id.id}) for order in orders]
            else:
                self.order_ids = [(0, 0, {'name': order.name,
                                          'state': order.state,
                                          'date_order': order.date_order,
                                          'user_id': order.user_id.id,
                                          'team_id': order.team_id.id,
                                          'billing_type': order.billing_type,
                                          'type': order.type,
                                          'partner_id': order.partner_id.id}) for order in (orders & order_ids)]
