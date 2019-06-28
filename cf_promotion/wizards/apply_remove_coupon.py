# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
import logging
from odoo.exceptions import Warning

class ApplyRemoveCoupon(models.TransientModel):
    _name = 'apply.remove.coupon'

    name = fields.Char("Coupon")

    @api.model
    def default_get(self, fields):
        order_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        if order_id.state <> 'draft':
            raise Warning(_("You only execute this function when order is in the Quotation state."))
        res = super(ApplyRemoveCoupon, self).default_get(fields)
        res.update({
            'name': order_id.coupon or '',
        })
        return res

    @api.multi
    def action_apply(self):
        order_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        if order_id.state <> 'draft':
            raise Warning(_("You only execute this function when order is in the Quotation state."))
        order_id.write({'coupon': self.name or False})
        order_id.update_price_by_odoo()