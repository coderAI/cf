# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from lxml import etree
from datetime import datetime, timedelta


class RemoveAttendanceWizard(models.TransientModel):
    _name = 'remove.attendance.wizard'

    in_money = fields.Float(string='Non-CheckIn Fine', default=0)
    out_money = fields.Float(string='Non-CheckOut Fine', default=0)
    check_in = fields.Boolean(string='Non-CheckIn Fine')
    check_out = fields.Boolean(string='Non-CheckOut Fine')
    name = fields.Char(string='Reason')
    multi = fields.Boolean(string='Multi Remove')

    @api.model
    def default_get(self, fields_list):
        res = super(RemoveAttendanceWizard, self).default_get(fields_list)
        attendance_id = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_ids'))
        if len(attendance_id) <= 1:
            res.update({
                'in_money': attendance_id.in_money,
                'out_money': attendance_id.out_money,
                'multi': False
            })
        else:
            res.update({
                'multi': True
            })
        return res

    @api.multi
    def action_apply(self):
        attendance_ids = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_ids'))
        if len(attendance_ids) <= 1:
            attendance_ids.filtered(lambda att: (att.in_money > 0 or att.out_money > 0) and (self.env.user in att.remover or self.user_has_groups('hr_attendance.group_hr_attendance_user'))).write({
                'in_money': self.in_money,
                'out_money': self.out_money,
                'reason': self.name,
                'user_id': self._uid,
                'date_remove': datetime.now()
            })
        else:
            if self.check_in:
                attendance_ids.filtered(lambda att: att.in_money > 0 and (self.env.user in att.remover or self.user_has_groups('hr_attendance.group_hr_attendance_user'))).write({
                    'in_money': 0,
                    'reason': self.name,
                    'user_id': self._uid,
                    'date_remove': datetime.now()
                })
            if self.check_out:
                attendance_ids.filtered(lambda att: att.out_money > 0 and (self.env.user in att.remover or self.user_has_groups('hr_attendance.group_hr_attendance_user'))).write({
                    'out_money': 0,
                    'reason': self.name,
                    'user_id': self._uid,
                    'date_remove': datetime.now()
                })