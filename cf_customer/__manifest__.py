{
    'name': 'CloudFone Customer',
    'category': 'cf',
    'author': 'uviah',
    'description': 'Customer customize',
    'depends': [
        'base',
        'cf_security',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/res_partner.xml',
        'wizards/generate_code_wizard.xml',
        'wizards/search_customer_wizard.xml',
        'views/res_partner.xml',
    ],
    'installable': True,
}