{
    'name': 'CloudFone Promotion',
    'category': 'cloudfone',
    'author': 'uviah',
    'description': 'Promotion Configuration',
    'depends': [
        'cf_sale',
        'cf_customer',
    ],
    'data': [
        # Group
        'security/res_group.xml',
        # Security
        'security/ir.model.access.csv',
        # Wizard
        'wizards/coupon_setting_wizard.xml',
        'wizards/promotion_conditional_wizard.xml',
        'wizards/promotion_coupon_wizard.xml',
        'wizards/apply_remove_coupon.xml',
        # Views
        'views/coupon.xml',
        'views/promotion.xml',
        'views/dashboard.xml',
        'views/sale_order.xml',
        # 'views/product_category.xml',
        'views/web_assets.xml',
        # Menu
        'menu/menu.xml',
    ],
    'installable': True,
}