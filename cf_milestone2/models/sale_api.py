# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleAPI(models.AbstractModel):
    _description = 'External SO API'
    _name = 'sale.api'
    _inherit = 'sale.api'

    @api.model
    def confirm_order(self, order):
        SaleOrder = self.env['sale.order']
        if type(order) is int:
            order_id = SaleOrder.browse(order)
        else:
            order_id = SaleOrder.search([('name', '=', order)])
        if not order_id:
            return {'"code"': 0, '"msg"': '"Order not found"'}
        if len(order_id) > 1:
            return {'"code"': 0, '"msg"': '"Have %s Order"' % len(order_id)}
        if order_id.state not in ('draft', 'waiting'):
            return {'"code"': 0, '"msg"': '"State of Order must be in Quotation or Waiting"'}
        order_id.action_confirm()
        return {'"code"': 1, '"msg"': '"Successfully"'}

    @api.model
    def active_order(self, order):
        SaleOrder = self.env['sale.order']
        if type(order) is int:
            order_id = SaleOrder.browse(order)
        else:
            order_id = SaleOrder.search([('name', '=', order)])
        if not order_id:
            return {'"code"': 0, '"msg"': '"Order not found"'}
        if len(order_id) > 1:
            return {'"code"': 0, '"msg"': '"Have %s Order"' % len(order_id)}
        if order_id.state != 'paid':
            return {'"code"': 0, '"msg"': '"Pls paid for Order %s"' % order_id.name}
        try:
            order_id.order_line.filtered(lambda line: line.service_status == 'draft').activate()
            return {'"code"': 1, '"msg"': '"Successfully"'}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

