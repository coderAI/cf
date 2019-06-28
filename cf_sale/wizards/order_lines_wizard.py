# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import Warning
from datetime import datetime, timedelta
import logging


class OrderLinesWizard(models.TransientModel):
    _name = "order.lines.wizard"
    _description = "a sales order line in service.addon.order.lines.wizard"

    @api.model
    def _get_selection_register_type(self):
        order_id = self._context.get('order_id') or (
                    self._context.get('active_model') == 'sale.order' and self._context.get('active_id'))
        order = self.env['sale.order'].browse(order_id)
        lst = [('register', 'Register'),
               ('renew', 'Renew')]
        if not order.team_id or order.team_id.type in ('sale', False):
            lst = [('register', 'Register')]
        return lst

    parent_id = fields.Many2one('service.addon.order.lines.wizard', 'Parent')
    is_service = fields.Boolean(string="is Service product")
    register_type = fields.Selection(string="Register Type", selection='_get_selection_register_type',
        # selection=[('register', 'Register'),
        #            ('renew', 'Renew'),
        #            ('upgrade', 'Upgrade')],
        required=True)
    product_category_id = fields.Many2one(
        'product.category', string="Product Category", required=True)
    product_id = fields.Many2one(
        "product.product", string="Product")
    product_name = fields.Char(
        string="Product Name")
    time = fields.Float(string="Time", required=True)
    product_uom_id = fields.Many2one('product.uom', string="UOM", compute="get_uom")
    parent_product_id = fields.Many2one(
        'product.product', string="Parent Service")
    notes = fields.Char(string='Notes')
    billing_type = fields.Selection([('prepaid', 'Prepaid'), ('postpaid', 'Postpaid')], "Billing Type")

    @api.model
    def default_get(self, fields):
        res = super(OrderLinesWizard, self).default_get(fields)
        order_id = self.env['sale.order'].browse(self._context.get('order_id'))
        res.update({
            'billing_type': order_id.billing_type,
            'time': 1
        })
        return res

    @api.multi
    def get_parent_product_category(self, categ_id):
        if categ_id and categ_id.parent_id:
            return self.get_parent_product_category(categ_id.parent_id)
        else:
            return categ_id

    @api.depends('product_category_id')
    def get_uom(self):
        for line in self:
            if line.product_category_id:
                line.product_uom_id = line.product_category_id.uom_id.id

    @api.onchange('register_type')
    def onchange_register_type(self):
        self.product_category_id = False
        self.product_name = False
        self.parent_product_id = False
        if not self.register_type:
            return {'domain': {'product_category_id': [('id', '=', False)]}}
        # order_id = self.env['sale.order'].browse(self._context.get('order_id'))
        # domain = [('id', 'child_of', order_id.category_id.id)]
        domain = []
        if self.register_type == 'renew':
            domain.append(('can_be_renew', '=', True))
        else:
            domain.append(('can_be_register', '=', True))
        if self._context.get('default_is_service', False):
            domain.append(('is_addons', '=', False))
        else:
            domain.append(('is_addons', '=', True))
        return {'domain': {'product_category_id': domain}}

    @api.onchange('product_category_id')
    def onchange_product_category_id(self):
        logging.info("00000000000000000000000 %s", self._context)
        self.product_id = False
        order_id = self.env['sale.order'].browse(self._context.get('order_id'))
        if not self._context.get('default_is_service', False):
            if self.register_type != 'renew':
                if self.product_category_id:
                    prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                    min_qty = self.product_category_id.minimum_register_time
                    if float_compare(self.time, min_qty, prec) < 0 and order_id.billing_type == 'prepaid':
                        self.time = min_qty
                    parent_categ = self.get_parent_product_category(self.product_category_id)
                    product_id = self.env['sale.service'].search(
                        [('customer_id', '=', order_id.partner_id.id),
                         ('status', '=', 'active'),
                         ('product_category_id.is_addons', '=', False)]).mapped('product_id')
                    product_ids = product_id and product_id.ids or []
                    if order_id.order_line:
                        line_ids = order_id.order_line.filtered(
                            lambda l: l.product_category_id.parent_id and
                                      self.get_parent_product_category(l.product_category_id) == parent_categ and
                                      l.product_category_id.is_addons == False).mapped('product_id')
                        product_ids = list(set(product_ids + line_ids.ids)) if line_ids else product_ids
                    self.product_name = self.product_category_id.name
                    return {
                        'domain': {
                            'parent_product_id': [('id', 'in', product_ids)]
                        }
                    }
            else:
                if self.product_category_id:
                    if not order_id.team_id or order_id.team_id.type in ('sale', False):
                        product_id = self.env['sale.service'].search(
                            [('customer_id', '=', order_id.partner_id.id),
                             ('product_category_id', '=', self.product_category_id.id),
                             ('status', '=', 'active'),
                             ('start_date', '>=', (datetime.now().date() -
                                                   timedelta(days=30)).strftime('%Y-%m-%d'))]).mapped('product_id')
                    else:
                        product_id = self.env['sale.service'].search(
                            [('customer_id', '=', order_id.partner_id.id),
                             ('product_category_id', '=', self.product_category_id.id),
                             ('status', '=', 'active')]).mapped('product_id')
                    product_ids = product_id and product_id.ids or []
                    if not order_id.team_id or order_id.team_id.type in ('sale', False):
                        service_close_ids = self.env['sale.service'].search(
                            [('customer_id', '=', order_id.partner_id.id),
                             ('product_category_id', '=', self.product_category_id.id),
                             ('status', '=', 'closed'),
                             ('end_date', '>=', (datetime.now().date() - timedelta(days=15)).strftime('%Y-%m-%d')),
                             ('start_date', '>=', (datetime.now().date() -
                                                   timedelta(days=30)).strftime('%Y-%m-%d'))])
                    else:
                        service_close_ids = self.env['sale.service'].search(
                            [('customer_id', '=', order_id.partner_id.id),
                             ('product_category_id', '=', self.product_category_id.id),
                             ('status', '=', 'closed'),
                             ('end_date', '>=', (datetime.now().date() - timedelta(days=15)).strftime('%Y-%m-%d'))])
                    product_ids += service_close_ids and service_close_ids.mapped('product_id').ids or []
                    return {'domain': {'product_id': [('id', 'in', product_ids)]}}
        else:
            if self.register_type == 'register' and self.product_category_id:
                self.product_name = self.product_category_id.name
            if self.register_type == 'renew' and self.product_category_id:
                logging.info("11111111111, %s", order_id.team_id and order_id.team_id.type or False)
                if not order_id.team_id or order_id.team_id.type in ('sale', False):
                    product_id = self.env['sale.service'].search(
                        [('customer_id', '=', order_id.partner_id.id),
                         ('status', '=', 'active'),
                         ('product_category_id', '=', self.product_category_id.id),
                         ('start_date', '>=', (datetime.now().date() -
                                               timedelta(days=30)).strftime('%Y-%m-%d'))]).mapped('product_id')
                    logging.info("22222222222 %s", product_id)
                else:
                    product_id = self.env['sale.service'].search(
                        [('customer_id', '=', order_id.partner_id.id),
                         ('status', '=', 'active'),
                         ('product_category_id', '=', self.product_category_id.id)]).mapped('product_id')
                product_ids = product_id and product_id.ids or []
                if not order_id.team_id or order_id.team_id.type in ('sale', False):
                    service_close_ids = self.env['sale.service'].search(
                        [('customer_id', '=', order_id.partner_id.id),
                         ('product_category_id', '=', self.product_category_id.id),
                         ('status', '=', 'closed'),
                         ('end_date', '>=', (datetime.now().date() - timedelta(days=15)).strftime('%Y-%m-%d')),
                         ('start_date', '>=', (datetime.now().date() -
                                               timedelta(days=30)).strftime('%Y-%m-%d'))])
                else:
                    service_close_ids = self.env['sale.service'].search(
                        [('customer_id', '=', order_id.partner_id.id),
                         ('product_category_id', '=', self.product_category_id.id),
                         ('status', '=', 'closed'),
                         ('end_date', '>=', (datetime.now().date() - timedelta(days=15)).strftime('%Y-%m-%d'))])
                product_ids += service_close_ids and service_close_ids.mapped('product_id').ids or []
                return {
                    'domain': {
                        'product_id': [('id', 'in', product_ids)]
                    }
                }


