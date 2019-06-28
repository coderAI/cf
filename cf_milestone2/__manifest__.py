{
    'name': 'ODS Milestone2',
    'category': 'ods',
    'author': 'uviah',
    'description': 'ODS Milestone2 customize',
    'depends': [
        'base',
        'ods_customer',
        'ods_api',
        'account',
    ],
    'data': [
        # Data
        'data/reset_password_template.xml',
        # Wizards
        'wizards/generate_code_wizard.xml',
        # Views
        # 'views/res_partner.xml',
        # Report
        'reports/contract_customer_report.xml',
    ],
    'installable': True,
}