{
    'name': 'CloudFone Product',
    'category': 'cloudfone',
    'author': 'uviah',
    'description': 'Product customize',
    'depends': [
        'product',
        'sales_team',
        'sale',
        'stock_account',
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/product_category.xml',
        'views/product_agency_price.xml',
        'views/product.xml',
    ],
    'installable': True,
}