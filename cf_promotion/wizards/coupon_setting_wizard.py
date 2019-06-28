# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CouponSettingWizard(models.TransientModel):
    _name = 'coupon.setting.wizard'

    expired_date = fields.Datetime()
    max_used_time = fields.Integer()
    invisible_on_sale = fields.Boolean("Invisible on Sale")

    @api.model
    def default_get(self, fields):
        res = super(CouponSettingWizard, self).default_get(fields)
        coupon_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        res.update({
            'expired_date': coupon_id.expired_date,
            'max_used_time': coupon_id.max_used_time,
            'invisible_on_sale': coupon_id.invisible_on_sale,
        })
        return res

    @api.multi
    def btn_settings(self):
        if not self.expired_date and not self.max_used_time:
            return {}
        coupons = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        if coupons:
            coupons.write({
                'expired_date': self.expired_date,
                'max_used_time': self.max_used_time,
                'invisible_on_sale': self.invisible_on_sale
            })
        return {}
