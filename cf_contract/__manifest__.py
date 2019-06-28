{
    'name': 'CloudFone Contract',
    'category': 'cf',
    'author': 'uviah',
    'description': 'Contract customize',
    'depends': [
        'cf_sale',
        'report_py3o',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/cf_contract.xml',
        'views/sale_order.xml',
        'views/res_partner.xml',
        'views/menu.xml',
        'reports/contract_report.xml',
    ],
    'installable': True,
}