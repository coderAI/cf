# -*- coding: utf-8 -*-
from odoo import api, fields, models
from .sale_order_line import REGISTER_TYPE


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order Line')
    register_type = fields.Selection(REGISTER_TYPE, 'Register Type', readonly=False)
    notes = fields.Char(string='Notes')
