# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
import logging as _logger

class HrHolidays(models.Model):
    _inherit = 'hr.holidays'

    leave_type = fields.Selection([
        ('morning', 'Morning'), ('afternoon', 'Afternoon'), ('all', 'All')
    ], string='Type')
    approver = fields.Many2many('res.users', 'holidays_users_rel', 'holiday_id', 'user_id', string='Approvers',
                                compute='check_approve', store=True)
    approve = fields.Boolean(string='Can Approve', compute='check_is_approve',
                             help="If return True, show button Approve.")
    nod = fields.Float('Allocation', compute='_compute_nod')

    @api.multi
    @api.depends('number_of_days_temp')
    def _compute_nod(self):
        for holiday in self:
            holiday.nod = holiday.number_of_days_temp

    @api.onchange('date_from', 'leave_type')
    def _onchange_date_from(self):
        super(HrHolidays, self)._onchange_date_from()
        # if self.date_from and self.date_to:
        if self.type == 'remove':
            if self.leave_type in ('morning', 'afternoon'):
                self.number_of_days_temp = 0.5
            elif self.leave_type == 'all' and self.date_from and self.date_to:
                from_dt = fields.Datetime.from_string(self.date_from)
                to_dt = fields.Datetime.from_string(self.date_to)
                if from_dt.date() == to_dt.date():
                    self.number_of_days_temp = 1
                else:
                    days = (to_dt.date() - from_dt.date()).days + 1
                    self.number_of_days_temp = days

    @api.onchange('date_to', 'leave_type')
    def _onchange_date_to(self):
        super(HrHolidays, self)._onchange_date_to()
        if self.type == 'remove':
            # if self.date_from and self.date_to:
            if self.leave_type in ('morning', 'afternoon'):
                self.number_of_days_temp = 0.5
            elif self.leave_type == 'all' and self.date_from and self.date_to:
                from_dt = fields.Datetime.from_string(self.date_from)
                to_dt = fields.Datetime.from_string(self.date_to)
                if from_dt.date() == to_dt.date():
                    self.number_of_days_temp = 1
                else:
                    days = (to_dt.date() - from_dt.date()).days + 1
                    self.number_of_days_temp = days

    @api.multi
    def action_validate(self):
        res = super(HrHolidays, self).action_validate()
        for record in self.filtered(lambda l: l.type == 'remove'):
            attendance_ids = self.env['hr.attendance'].search([('employee_id', '=', record.employee_id.id),
                                                               ('date_att', '>=', datetime.strptime(record.date_from,
                                                                                                    '%Y-%m-%d %H:%M:%S').date()),
                                                               ('date_att', '<=', datetime.strptime(record.date_to,
                                                                                                    '%Y-%m-%d %H:%M:%S').date())])
            if attendance_ids:
                for att in attendance_ids:
                    if self.leave_type == 'morning':
                        att.write({
                            'leave': True,
                            'in_money': 0,
                        })
                    elif self.leave_type == 'afternoon':
                        att.write({
                            'leave': True,
                            'out_money': 0,
                        })
                    else:
                        att.write({
                            'leave': True,
                            'in_money': 0,
                            'out_money': 0,
                        })
        return res

    def recursive_user_approve(self, employee_id, users):
        approvers = employee_id.holidays_approvers and employee_id.holidays_approvers.mapped('approver') or False
        if approvers:
            users += approvers.mapped('user_id') and approvers.mapped('user_id').ids or []
            for employee in approvers - employee_id:
                self.recursive_user_approve(employee, users)
            return users
        else:
            return users

    @api.depends('employee_id', 'employee_id.holidays_approvers')
    def check_approve(self):
        for record in self:
            if record.employee_id:
                record.approver = [(6, 0, record.recursive_user_approve(record.employee_id, []))]

    def check_is_approve(self):
        for record in self:
            record.approve = False
            if self.env.user in record.approver and record.state != 'validate':
                record.approve = True
            if self.user_has_groups('hr_holidays.group_hr_holidays_user') and record.state != 'validate':
                record.approve = True

    @api.multi
    def action_confirm(self):
        for leave in self:
            try:
                approver_ids = leave.mapped('employee_id').mapped('holidays_approvers').mapped('approver')
                email_to = approver_ids and ';'.join(approver.work_email for approver in approver_ids)
                if email_to:
                    parameters = self.env['ir.config_parameter'].search([('key', '=', 'web.base.url')])
                    _logger.info("-------------------- %s --------------------" % parameters)
                    if parameters:
                        view_url = parameters[0].value
                        view_url += '/web?#id=%s&view_type=form&model=hr.holidays' % leave.id
                    else:
                        view_url = 'https://erponline.matbao.com'
                    url = u'<a href="%s"><strong>tại đây</strong></a>' % (view_url,)
                    msg = u'<p>Chào bạn,</p><p>Nhân viên %s xin nghỉ phép.</p><p>Nội dung: %s</p>' \
                          u'<p>Loại nghỉ phép: %s</p><p>Thời gian: %s - %s (%s days)</p>' % \
                          (leave.employee_id and leave.employee_id.name, leave.name or '', leave.holiday_status_id and leave.holiday_status_id.name or '',
                           leave.date_from or '', leave.date_to or '', leave.number_of_days_temp)
                    footer = u'<p>Vui lòng truy cập %s để xem thông tin và duyệt phép.</p>' % (url,)
                    mail_values = {
                        'email_from': self.env.user.email,
                        'email_to': email_to,
                        'subject': u"V/v Nhân viên %s xin nghỉ phép" % leave.employee_id.name,
                        'body_html': msg + footer,
                        'body': msg + footer,
                        'notification': True,
                        'author_id': self.env.user.partner_id.id,
                        'message_type': "email",
                    }
                    mail_id = self.env['mail.mail'].create(mail_values)
                    mail_id.send()
            except Exception as e:
                _logger.info("Can't send email: %s" % (e.message or repr(e)))
                pass
        return super(HrHolidays, self).action_confirm()

    @api.model
    def create(self, vals):
        leave = super(HrHolidays, self).create(vals)
        try:
            approver_ids = leave.mapped('employee_id').mapped('holidays_approvers').mapped('approver')
            email_to = approver_ids and ';'.join(approver.work_email for approver in approver_ids)
            if email_to:
                parameters = self.env['ir.config_parameter'].search([('key', '=', 'web.base.url')])
                _logger.info("-------------------- %s --------------------" % parameters)
                if parameters:
                    view_url = parameters[0].value
                    view_url += '/web?#id=%s&view_type=form&model=hr.holidays' % leave.id
                else:
                    view_url = 'https://erponline.matbao.com'
                url = u'<a href="%s"><strong>tại đây</strong></a>' % (view_url,)
                msg = u'<p>Chào bạn,</p><p>Nhân viên %s xin nghỉ phép.</p><p>Nội dung: %s</p>' \
                      u'<p>Loại nghỉ phép: %s</p><p>Thời gian: %s - %s (%s days)</p>' % \
                      (leave.employee_id and leave.employee_id.name, leave.name or '', leave.holiday_status_id and leave.holiday_status_id.name or '',
                       leave.date_from or '', leave.date_to or '', leave.number_of_days_temp)
                footer = u'<p>Vui lòng truy cập %s để xem thông tin và duyệt phép.</p>' % (url,)
                mail_values = {
                    'email_from': self.env.user.email,
                    'email_to': email_to,
                    'subject': u"V/v Nhân viên %s xin nghỉ phép" % leave.employee_id.name,
                    'body_html': msg + footer,
                    'body': msg + footer,
                    'notification': True,
                    'author_id': self.env.user.partner_id.id,
                    'message_type': "email",
                }
                mail_id = self.env['mail.mail'].create(mail_values)
                mail_id.send()
        except Exception as e:
            _logger.info("Can't send email: %s" % (e.message or repr(e)))
            pass
        return leave

    @api.multi
    def action_approve(self):
        for holiday in self:
            current_user = self.env.user
            holiday.sudo().with_context(default_author=current_user.partner_id.id, approver=current_user.id).action_validate()
        for record in self.filtered(lambda l: l.type == 'remove'):
            attendance_ids = self.env['hr.attendance'].search([('employee_id', '=', record.employee_id.id),
                                                               ('date_att', '>=', datetime.strptime(record.date_from,
                                                                                                    '%Y-%m-%d %H:%M:%S').date()),
                                                               ('date_att', '<=', datetime.strptime(record.date_to,
                                                                                                    '%Y-%m-%d %H:%M:%S').date())])
            if attendance_ids:
                for att in attendance_ids:
                    if self.leave_type == 'morning':
                        att.write({
                            'leave': True,
                            'in_money': 0,
                        })
                    elif self.leave_type == 'afternoon':
                        att.write({
                            'leave': True,
                            'out_money': 0,
                        })
                    else:
                        att.write({
                            'leave': True,
                            'in_money': 0,
                            'out_money': 0,
                        })

    # def _get_number_of_days(self, date_from, date_to, employee_id):
    #     number_of_days = super(HrHolidays, self)._get_number_of_days(date_from, date_to, employee_id)
    #     if self.leave_type in ('morning', 'afternoon'):
    #         number_of_days = 0.5
    #     elif self.leave_type == 'all':
    #         from_dt = fields.Datetime.from_string(date_from)
    #         to_dt = fields.Datetime.from_string(date_to)
    #         if from_dt.date() == to_dt.date():
    #             number_of_days = 1
    #         else:
    #             number_of_days = to_dt.date() - from_dt.date()
    #     return number_of_days


class EmployeeHolidaysApprobation(models.Model):
    _inherit = "hr.employee.holidays.approbation"

    @api.model
    def create(self, vals):
        if self._context.get('approver'):
            vals['approver'] = self._context.get('approver')
        return super(EmployeeHolidaysApprobation, self).create(vals)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        if self._context.get('default_author'):
            if vals.get('author_id') <> self._context.get('default_author'):
                vals['author_id'] = self._context.get('default_author')
        return super(MailMessage, self).create(vals)