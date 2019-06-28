# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class UpgradeServivceWizard(models.TransientModel):
    _name = 'upgrade.service.wizard'

    old_category_id = fields.Many2one('product.category', string='Old Category')
    service_id = fields.Many2one('sale.service', string='Service')
    start_date = fields.Date(string='Start Date', related="service_id.start_date", readonly=True)
    end_date = fields.Date(string='End Date', related="service_id.end_date", readonly=True)
    new_category_id = fields.Many2one('product.category', string='New Category')
    time = fields.Float('Register Time', digits=(16, 0))
    uom_id = fields.Many2one('product.uom', string='UOM', related="new_category_id.uom_id")
    refund_amount = fields.Float('Refund Amount (Untaxed)', digits=(16, 0))
    up_price = fields.Float(string='Up Price', default=0)
    license = fields.Integer()

    @api.depends('customer_id', 'old_category_id')
    def get_services(self):
        order_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        if order_id.partner_id and self.old_category_id:
            service_ids = self.env['sale.service'].search([('customer_id', '=', order_id.partner_id.id),
                                                           ('product_category_id', '=', self.old_category_id.id),
                                                           ('status', '=', 'active')])
            services = service_ids and service_ids.ids or []
            service_close_ids = self.env['sale.service'].search([('customer_id', '=', order_id.partner_id.id),
                                                                 ('product_category_id', '=',
                                                                  self.old_category_id.id),
                                                                 ('status', '=', 'closed')]).filtered(
                lambda s: s.end_date >= (datetime.now().date() - timedelta(days=15)).strftime('%Y-%m-%d'))
            services += service_close_ids and service_close_ids.ids or []
            self.service_ids = [(6, 0, services)]

    @api.constrains('refund_amount', 'new_category_id', 'license', 'time')
    def _check_amount(self):
        if self.new_category_id and self.refund_amount and self.time:
            price = self.time * self.new_category_id.renew_price * (self.license or 1)# - (self.refund_amount or 0)
            if self.refund_amount > price:
                raise UserError(_("Refund Amount can't larger than Price Renew Tax: %s" % price))

    @api.onchange('old_category_id')
    def onchange_old_category_id(self):
        order_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        if order_id.partner_id and self.old_category_id:
            service_ids = self.env['sale.service'].search([('customer_id', '=', order_id.partner_id.id),
                                                           ('product_category_id', '=', self.old_category_id.id),
                                                           ('status', '=', 'active')])
            services = service_ids and service_ids.ids or []
            service_close_ids = self.env['sale.service'].search([('customer_id', '=', order_id.partner_id.id),
                                                                 ('product_category_id', '=', self.old_category_id.id),
                                                                 ('status', '=', 'closed')]).filtered(
                lambda s: s.end_date >= (datetime.now().date() - timedelta(days=15)).strftime('%Y-%m-%d'))
            services += service_close_ids and service_close_ids.ids or []
            return {'domain': {
                        'service_id': [('id', 'in', services)],
                        'new_category_id': [('id', 'in', self.old_category_id.cf_product_category_ids and
                                                         self.old_category_id.cf_product_category_ids.ids or False)]
                    }
            }
        else:
            return {'domain': {
                        'service_id': [('id', '=', False)],
                        'new_category_id': [('id', '=', False)]
                    }
            }

    @api.multi
    def action_add(self):
        order_line = [(0, 0, {'register_type': 'upgrade',
                              'product_category_id': self.new_category_id and self.new_category_id.id or False,
                              'old_category_id': self.old_category_id and self.old_category_id.id or False,
                              'product_id': self.service_id and self.service_id.product_id and self.service_id.product_id.id or False,
                              'time': self.time or 0,
                              'original_time': self.time or 0,
                              'product_uom': self.uom_id and self.uom_id.id or False,
                              'up_price': self.up_price or 0,
                              # 'tax_id': self.tax_id and [(6, 0, [self.tax_id.id])] or [],
                              'price_updated': False,
                              'refund_amount': self.refund_amount or 0,
                              'license': self.license})]
        # Sale order
        order_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        order_id.write({
            'order_line': order_line
        })