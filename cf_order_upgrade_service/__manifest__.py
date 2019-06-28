{
    'name': 'CloudFone Order Upgrade Service',
    'category': 'cloudfone',
    'author': 'vuhai',
    'description': 'Upgrade service in Order',
    'depends': [
        'cf_sale',
    ],
    'data': [
        'wizards/upgrade_service_wizard.xml',
        'views/sale_order.xml',
    ],
    'installable': True,
}