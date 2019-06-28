# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order Line')
    is_active = fields.Boolean(string="Is Active", default=False, track_visibility='onchange')
    sale_order_id = fields.Many2one('sale.order', related='sale_order_line_id.order_id', string='Sale Order')
    customer_id = fields.Many2one('res.partner', "Customer")
    service_id = fields.Many2one('sale.service', "Service")

    @api.multi
    def button_cancel(self):
        res = super(PurchaseOrder, self).button_cancel()
        for po in self:
            if po.sale_order_line_id:
                po.sale_order_line_id.write({
                    'service_status': 'refused'
                })
        return res

    @api.multi
    def action_active(self):
        for order in self:
            if not order.is_active:
                order.is_active = True
            if order.order_line:
                for line in order.order_line:
                    if line.sale_order_line_id:
                        line.sudo().sale_order_line_id.write({'service_status': 'done'})