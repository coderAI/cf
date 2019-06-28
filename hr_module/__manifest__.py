{
    'name': 'HR Module',
    'category': 'ods/cloudfone',
    'author': 'uviah',
    'description': 'Customize HR: Employee, Leaves, Attendance',
    'depends': [
        'base',
        'hr_attendance',
        'hr_holidays',
        'hr_holidays_multi_levels_approval',
    ],
    'data': [
        # Wizards
        'wizards/remove_attendance_wizard.xml',
        # Views
        'views/hr_employee.xml',
        'views/hr_holidays.xml',
        'views/attendance_details.xml',
        'views/hr_attendance.xml',
        # Reports
        'reports/attendance_report.xml',
        # Menu
        'menu/menu.xml',
        # Security
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
    ],
    'installable': True,
}