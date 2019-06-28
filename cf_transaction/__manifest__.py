{
    'name': 'CloudFone Transaction',
    'category': 'cloudfone',
    'author': 'uviah',
    'description': 'Bank Transaction',
    'depends': [
        'payment',
        'cf_security',
        'account_reports',
        'account_asset',
    ],
    'data': [
        # Data
        'data/ir_sequence.xml',
        # Security
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        # Views
        'views/money_transfer.xml',
        'views/bank_transaction.xml',
        'views/account_payment.xml',
        'views/transaction_config.xml',
        'views/account_journal_dashboard_view.xml',
        'views/web_asset.xml',
        # Reports
        'reports/report.xml',
        # Menu
        'menu/menu.xml',
    ],
    'installable': True,
}