{
    'name': 'MB E-invoice',
    'category': 'matbao',
    'version': '1.1.8',
    'sequence': 18,
    'author': 'Huy Snow',
        'description': """
E-invoice
==========================

This application enables you to manage invoice


You can manage:
---------------
* xxxxxx
* xxxxxx
* xxxxxx
    """,
    'depends': [
        'account',

    ],
    'data': [
        'views/stages_invoice_view.xml',
        'views/mb_e_invoice_api_config_view.xml',
        'views/mb_e_invoice_register_type_view.xml',
        'views/mb_reason_invoice_line_view.xml',
        'views/mb_reason_invoice_view.xml',
        'views/mb_e_invoice_view.xml',
        'views/account_invoice_view.xml',
        'wizards/mb_reason_invoice_line_wizard.xml',
        'wizards/mb_e_invoice_wizard.xml',
        'wizards/mb_e_invoice_set_done_wizard.xml',


        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        'menu/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

