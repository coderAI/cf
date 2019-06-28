# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning
from odoo.tools.float_utils import float_compare
from odoo.osv.orm import setup_modifiers
from odoo.tools.safe_eval import safe_eval
from lxml import etree

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    code = fields.Char(string='Employee Code', copy=False, readonly=True, index=True, track_visibility='onchange')
    remove_attendance = fields.Boolean(string='Remove Attendance', default=False)

    @api.model
    def get_list_employee(self):
        employee_ids = self.env['hr.employee'].search([])
        datas = []
        try:
            for employee in employee_ids:
                datas.append({
                    '"id"': employee.id,
                    '"name"': '"%s"' % employee.name,
                    '"department"': '"%s"' % (employee.department_id and employee.department_id.name or ''),
                    '"job"': '"%s"' % (employee.job_id and employee.job_id.name or ''),
                    '"mobile"': '"%s"' % (employee.mobile_phone or ''),
                    '"email"': '"%s"' % (employee.work_email or ''),
                    '"phone"': '"%s"' % (employee.work_phone or ''),
                    '"identification_id"': '"%s"' % (employee.identification_id or ''),
                    '"start_date"': '"%s"' % (employee.start_date or ''),
                    '"end_date"': '"%s"' % (employee.end_date or ''),
                    '"badge_id"': '"%s"' % (employee.barcode or ''),
                    '"pin"': '"%s"' % (employee.pin or ''),
                })
            return {'"code"': 1, '"msg"': '"Successfully"', '"data"': datas}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}