import pytz
from odoo import api, fields, models


class AttendanceDetals(models.Model):
    _name = 'hr.attendance.details'
    _description = "Attendance Details"

    employee_id = fields.Many2one('hr.employee', 'Employee')
    card_no = fields.Char('Card No', related='employee_id.pin')
    date_att = fields.Date('Date')
    check_in_out = fields.Datetime('Check In/Out')

    def name_get(self):
        res = []
        for record in self:
            name = '%s (%s)' % (record.employee_id.name, record.date_att)
            res.append((record.id, name))
        return res

    def convert_tz_to_utc(self, date_check):
        tz = pytz.timezone(self.env.user.tz or pytz.utc)
        tz_timestamp = tz.localize(date_check, is_dst=False)
        utc = pytz.timezone('UTC')
        return tz_timestamp.astimezone(utc)

    @api.model
    def sync_attendance_details(self, vals={}):
        if not vals or type(vals) is not dict:
            return {'"code"': 0, '"msg"': '"Invalid Data"'}
        args = {}
        if vals.get('card_no'):
            employee = self.env['hr.employee'].search([('pin', '=', vals['card_no'])])
            if not employee:
                return {'"code"': 0, '"msg"': '"Can not find Employee with Card No is %s"' % vals['card_no']}
            args['employee_id'] = employee.id
        else:
            return {'"code"': 0, '"msg"': '"Card No is not exist"'}
        if vals.get('check_in_out'):
            try:
                date_check = self.convert_tz_to_utc(fields.Datetime.from_string(vals['check_in_out']))
                args['date_att'] = date_check
                args['check_in_out'] = date_check
            except ValueError as e:
                return {'"code"': 0, '"msg"': '"Can not create Attendance Details: %s"' % (e.message or repr(e))}
        else:
            return {'"code"': 0, '"msg"': '"Date Check In / Out is not exist"'}
        try:
            self.create(args)
            return {'"code"': 1, '"msg"': '"Create successfully Attendance Details"'}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Can not create Attendance Details: %s"' % (e.message or repr(e))}
