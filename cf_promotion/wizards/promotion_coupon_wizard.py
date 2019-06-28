# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning
import string
import random
from datetime import datetime


class PromotionCouponWizard(models.TransientModel):
    _name = 'promotion.coupon.wizard'

    type = fields.Selection([('once', 'Once'), ('many', 'Many')], string="Use Times", default='once')
    expired_date = fields.Datetime("Expired Date")
    amount_coupon = fields.Integer("Amount Coupon")
    coupon = fields.Char()
    invisible_on_sale = fields.Boolean("Invisible on Sale")

    @api.model
    def default_get(self, fields):
        res = super(PromotionCouponWizard, self).default_get(fields)
        promotion_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        res.update({
            'expired_date': promotion_id.date_to
        })
        return res

    def generate_code(self, leng, arr=[]):
        """ The leng is the length of the coupon code, arr is the list of available coupons"""
        code = ''.join(random.choice(string.ascii_uppercase + string.digits[1:]) for _ in range(leng))
        code_exists = self.env['mb.coupon'].search_count([('name', '=', code), ('name', 'in', arr)])
        if code_exists:
            self.generate_code(leng)
        return code

    @api.multi
    def create_coupon(self):
        MBCoupon = self.env['mb.coupon']
        promotion_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        if self.type == 'once':
            coupon_vals = []
            for i in range(0, self.amount_coupon):
                coupon_vals.append(self.generate_code(7, coupon_vals))
            if coupon_vals:
                cr = self._cr
                cr.execute("""INSERT INTO mb_coupon 
                                      (create_date, create_uid, write_date, write_uid, name, 
                                       promotion_id, expired_date, max_used_time, invisible_on_sale)
                                      SELECT %s, %s, %s, %s, unnest(%s), %s, %s, %s, %s""",
                           (datetime.now(), self._uid, datetime.now(), self._uid, coupon_vals,
                            promotion_id.id, self.expired_date, 1, self.invisible_on_sale))
        else:
            if self.env['mb.coupon'].search_count([('name', '=', self.coupon.strip())]):
                raise Warning("Coupon already exists. Pls enter another coupon")
            MBCoupon.create({
                'name': self.coupon,
                'promotion_id': promotion_id.id,
                'expired_date': self.expired_date,
                'max_used_time': self.amount_coupon,
                'invisible_on_sale': self.invisible_on_sale
            })


