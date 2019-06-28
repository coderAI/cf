# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

class MBCustomerType(models.Model):
    _name = 'mb.data.type'

    sequence = fields.Integer(string='Sequence', default=1)
    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    type = fields.Selection([('customer', 'Customer Type'), ('register', 'Register Type'),
                             ('service', 'Service Status'), ('order_type', 'Order Type'),
                             ('customer_level', 'Customer Level')], string='Type')