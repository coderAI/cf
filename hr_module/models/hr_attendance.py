# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from lxml import etree
from datetime import datetime, timedelta
import logging
from odoo.osv.orm import setup_modifiers
from odoo.addons.mail.models.mail_template import format_tz
import logging as _logger

class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = ["hr.attendance", 'mail.thread']
    _order = "date_att desc"

    check_in = fields.Datetime(string="Check In", required=False)
    date_att = fields.Date(string="Date")
    card_no = fields.Char(related='employee_id.pin', string='Card No')
    in_money = fields.Float(string='Non-CheckIn Fine', track_visibility='onchange')
    out_money = fields.Float(string='Non-CheckOut Fine', track_visibility='onchange')
    min_in = fields.Integer(string='Minutes CheckIn Late')
    min_out = fields.Integer(string='Minutes CheckOut Early')
    reason = fields.Char(string='Reason')
    user_id = fields.Many2one('res.users', string='User')
    date_remove = fields.Datetime(string='Remove Date')
    leave = fields.Boolean(string='Leave', compute='check_leave', store=True)
    remover = fields.Many2many('res.users', 'attendances_users_rel', 'attendance_id', 'user_id', string='Removers', compute='check_remove', store=True)
    remove = fields.Boolean(string='Can Remove', compute='check_is_remove', help="If return True, show button Remove Attendance.")

    def recursive_user_remove(self, employee_id, users):
        removers = employee_id.holidays_approvers and employee_id.holidays_approvers.mapped('approver') or False
        if removers:
            users += removers.mapped('user_id') and removers.mapped('user_id').ids or []
            for employee in removers - employee_id:
                self.recursive_user_remove(employee, users)
            return users
        else:
            return users

    @api.depends('employee_id', 'employee_id.holidays_approvers')
    def check_remove(self):
        for record in self:
            # record.remove = False
            if record.employee_id:
                record.remover = [(6, 0, record.recursive_user_remove(record.employee_id, []))]
            #     if self.env.user in record.remover:
            #         record.remove = True
            # if self.user_has_groups('hr_attendance.group_hr_attendance_user'):
            #     record.remove = True

    # @api.depends('remover')
    def check_is_remove(self):
        for record in self:
            record.remove = False
            if self.env.user in record.remover:
                # _logger.info("================================== 11111111111111111111111 ======================")
                record.remove = True
            if self.user_has_groups('hr_attendance.group_hr_attendance_user'):
                # _logger.info("================================== 22222222222222222222222 ======================")
                record.remove = True

    @api.depends('employee_id')
    def check_leave(self):
        for record in self:
            record.leave = False
            if record.employee_id:
                leave = self.env['hr.holidays'].search_count([('date_from', '<=', record.date_att), ('date_to', '>=', record.date_att),
                                                              ('state', '=', 'validate'), ('employee_id', '=', record.employee_id.id)])
                if leave:
                    record.leave = True

    @api.model
    def unlink_attendance_by_date(self, date):
        res = {'"code"': 0, '"msg"': '""'}
        Attendance = self.env['hr.attendance']
        attendance_ids = Attendance.search([('date_att', '=', date)])
        try:
            if attendance_ids:
                attendance_ids.unlink()
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Can`t unlink attendance: %s"' % (e.message or repr(e))}
        res['"msg"'] = '"Successfully"'
        res['"code"'] = 1
        return res

    @api.model
    def sync_attendances(self, card_no, date, check_in, check_out, in_money, out_money, min_in, min_out):
        res = {'"code"': 0, '"msg"': '""'}
        Employee = self.env['hr.employee']
        args = {}
        # Check type parameter
        if not card_no:
            return {'"msg"': '"Card No could not be empty."'}
        employee_id = Employee.search([('pin', '=', card_no)])
        if not employee_id:
            return {'"msg"': '"No employee with card no %s."' % card_no}
        if len(employee_id) > 1:
            return {'"msg"': '"Too many employee have card no %s."' % card_no}
        args.update({'employee_id': employee_id.id})
        if not date:
            return {'"msg"': '"Date could not be empty."'}
        args.update({'date_att': date})
        att_exists = self.search_count([('employee_id', '=', employee_id.id), ('date_att', '=', date)])
        if att_exists > 0:
            return {'"msg"': '"Attendance of %s have exists."' % employee_id.name}
        if check_in:
            args.update({'check_in': check_in})
        else:
            args.update({'check_in': False})
        if check_out:
            args.update({'check_out': check_out})
        # leave = self.env['hr.holidays'].search_count([('date_from', '<=', date), ('date_to', '>=', date), ('state', '=', 'validate'), ('employee_id', '=', employee_id.id)])
        cr = self.env.cr
        cr.execute("""SELECT id, leave_type
                      FROM hr_holidays
                      WHERE TYPE = 'remove'
                          AND state = 'validate'
                          AND employee_id = %s
                          AND date_from::DATE <= %s
                          AND date_to::DATE >= %s""", (employee_id.id, date, date))
        leave = cr.dictfetchall()
        if len(leave) > 0:
            if leave[0]['leave_type'] == 'morning':
                args.update({'in_money': 0})
            elif leave[0]['leave_type'] == 'afternoon':
                args.update({'out_money': 0})
            else:
                args.update({'in_money': 0, 'out_money': 0})
        else:
            if in_money:
                args.update({'in_money': in_money})
            if out_money:
                args.update({'out_money': out_money})
        if min_in:
            args.update({'min_in': min_in})
        if min_out:
            args.update({'min_out': min_out})
        try:
            # print args
            self.create(args)
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Can`t add attendance: %s"' % (e.message or repr(e))}
        res['"msg"'] = '"Successfully"'
        res['"code"'] = 1
        return res

    @api.model
    def get_list_card_no(self):
        Employee = self.env['hr.employee']
        employee_ids = Employee.search([('remove_attendance', '=', False), ('pin', '!=', False)])
        card_no = ['\"' + (emp.pin or '') + '\"' for emp in employee_ids]
        return {'"code"': 1, '"msg"': '"Completed"', '"data"': card_no}

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(HrAttendance, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'tree':
            if self.user_has_groups('base.group_system') or self.user_has_groups('hr_attendance.group_hr_attendance_user'):
                doc = etree.XML(res['arch'])
                tree_view = doc.xpath("//tree")
                tree_view[0].set('create', 'true')
                tree_view[0].set('delete', 'true')
                setup_modifiers(tree_view[0])
                res['arch'] = etree.tostring(doc)
            else:
                doc = etree.XML(res['arch'])
                tree_view = doc.xpath("//tree")
                tree_view[0].set('create', 'false')
                tree_view[0].set('delete', 'false')
                setup_modifiers(tree_view[0])
                res['arch'] = etree.tostring(doc)
        if view_type == 'form':
            if self.user_has_groups('base.group_system') or self.user_has_groups('hr_attendance.group_hr_attendance_user'):
                doc = etree.XML(res['arch'])
                form_view = doc.xpath("//form")
                form_view[0].set('create', 'true')
                form_view[0].set('edit', 'true')
                form_view[0].set('delete', 'true')
                setup_modifiers(form_view[0])
                res['arch'] = etree.tostring(doc)
            else:
                doc = etree.XML(res['arch'])
                form_view = doc.xpath("//form")
                form_view[0].set('create', 'false')
                form_view[0].set('edit', 'false')
                form_view[0].set('delete', 'false')
                setup_modifiers(form_view[0])
                res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def name_get(self):
        result = []
        for attendance in self:
            if not attendance.check_out:
                if not attendance.check_in:
                    result.append((self.id, _("%(empl_name)s from %(date_att)s") % {
                        'empl_name': self.employee_id.name_related,
                        'date_att': self.date_att,
                    }))
                else:
                    result.append((self.id, _("%(empl_name)s from %(check_in)s") % {
                        'empl_name': self.employee_id.name_related,
                        'check_in': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.check_in))),
                    }))
            else:
                result.append((self.id, _("%(empl_name)s from %(check_in)s to %(check_out)s") % {
                    'empl_name': self.employee_id.name_related,
                    'check_in': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.check_in))),
                    'check_out': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.check_out))),
                }))
        return result

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        for attendance in self:
            if not attendance.check_in and not attendance.check_out:
                last_attendance_before_check_in = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('date_att', '=', attendance.date_att),
                    ('id', '!=', attendance.id),
                ], order='date_att desc', limit=1)
                if last_attendance_before_check_in:
                    raise exceptions.ValidationError(_(
                        "Cannot create new attendance record for %(empl_name)s, the employee was already checked on %(datetime)s") % {
                                                         'empl_name': attendance.employee_id.name_related,
                                                         'datetime': attendance.date_att,
                                                     })
            else:
                # we take the latest attendance before our check_in time and check it doesn't overlap with ours
                last_attendance_before_check_in = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<=', attendance.check_in),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out >= attendance.check_in:
                    raise exceptions.ValidationError(_(
                        "Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                                                         'empl_name': attendance.employee_id.name_related,
                                                         'datetime': fields.Datetime.to_string(
                                                             fields.Datetime.context_timestamp(self,
                                                                                               fields.Datetime.from_string(
                                                                                                   attendance.check_in))),
                                                     })

                if not attendance.check_out:
                    # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                    no_check_out_attendances = self.env['hr.attendance'].search([
                        ('employee_id', '=', attendance.employee_id.id),
                        ('check_out', '=', False),
                        ('id', '!=', attendance.id),
                    ])
                    if no_check_out_attendances:
                        raise exceptions.ValidationError(_(
                            "Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s") % {
                                                             'empl_name': attendance.employee_id.name_related,
                                                             'datetime': fields.Datetime.to_string(
                                                                 fields.Datetime.context_timestamp(self,
                                                                                                   fields.Datetime.from_string(
                                                                                                       no_check_out_attendances.check_in))),
                                                         })
                else:
                    # we verify that the latest attendance with check_in time before our check_out time
                    # is the same as the one before our check_in time computed before, otherwise it overlaps
                    last_attendance_before_check_out = self.env['hr.attendance'].search([
                        ('employee_id', '=', attendance.employee_id.id),
                        ('check_in', '<=', attendance.check_out),
                        ('id', '!=', attendance.id),
                    ], order='check_in desc', limit=1)
                    if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                        raise exceptions.ValidationError(_(
                            "Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                                                             'empl_name': attendance.employee_id.name_related,
                                                             'datetime': fields.Datetime.to_string(
                                                                 fields.Datetime.context_timestamp(self,
                                                                                                   fields.Datetime.from_string(
                                                                                                       last_attendance_before_check_out.check_in))),
                                                         })


class MultiUpdateAttendance(models.Model):
    _name = 'multi.update.attendance'

    name = fields.Char(string="Name")
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    comment = fields.Char(string="Description")
    employee_ids = fields.Many2many('hr.employee', 'update_attendance_employee_rel', 'attendance_id', 'employee_id', string="Employees")
    type = fields.Selection([('allow', 'Allow'), ('except', 'Except')], string='Type', default='except')

    @api.multi
    def multi_update_attendance(self):
        args = []
        if self.date_from:
            args.append(('date_att', '>=', self.date_from))
        if self.date_to:
            args.append(('date_att', '<=', self.date_to))
        if self.type == 'except' and self.employee_ids:
            args.append(('employee_id', 'not in', self.employee_ids.ids))
        if self.type == 'allow' and self.employee_ids:
            args.append(('employee_id', 'in', self.employee_ids.ids))
        attendance_ids = self.env['hr.attendance'].search(args)
        attendance_ids.write({
            'in_money': 0,
            'out_money': 0,
            'reason': self.comment or self.name or '',
            'user_id': self._uid,
            'date_remove': datetime.now()
        })
