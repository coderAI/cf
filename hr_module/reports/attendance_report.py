# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class AttendanceReport(models.Model):
    _name = "attendance.report"
    _description = "Attendances Report"
    _auto = False

    employee_id = fields.Char(string='Employee', readonly=True)
    card_no = fields.Char(string='Card No', readonly=True)
    date_att = fields.Date(string='Date', readonly=True)
    check_in = fields.Datetime(string='Check In', readonly=True)
    check_out = fields.Datetime(string='Check Out', readonly=True)
    min_in = fields.Integer(string='Minutes CheckIn Late', readonly=True)
    min_out = fields.Integer(string='Minutes CheckOut Early', readonly=True)
    in_money = fields.Float(string='Non-CheckIn Fine', readonly=True)
    out_money = fields.Float(string='Non-CheckOut Fine', readonly=True)
    total_money = fields.Float(string='Total Fine', readonly=True)
    count_attendance = fields.Integer(string='Count', readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'attendance_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW attendance_report AS (                
                SELECT ha.id,
                    CASE
                        WHEN COALESCE(he.pin, '') <> '' THEN he.pin || ' - ' || he.name_related ELSE he.name_related
                    END AS employee_id,
                    he.pin AS card_no,
                    ha.date_att,
                    ha.check_in,
                    ha.check_out,
                    CASE WHEN ha.in_money <> 0.0 THEN ha.min_in ELSE 0 END AS min_in,
                    CASE WHEN ha.out_money <> 0.0 THEN ha.min_out ELSE 0 END AS min_out,
                    ha.in_money,
                    ha.out_money,
                    (COALESCE(ha.in_money, 0) + COALESCE(ha.out_money, 0)) AS total_money,
                    CASE WHEN ha.out_money <> 0.0 OR ha.in_money <> 0.0 THEN 1 ELSE 0 END AS count_attendance
                FROM hr_attendance ha
                LEFT JOIN hr_employee he ON he.id = ha.employee_id
            )
        """)
