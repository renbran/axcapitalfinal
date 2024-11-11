{
    'name': 'Sale Order Type',
    'version': '1.0',
    'author': 'Luna ERP Solutions',
    'website': 'https://www.lunerpsolution.com',
    'license': 'LGPL-3',
    'support': 'support@lunerpsolution.com',
    'category': 'Sales',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_type_views.xml',
        'views/sale_order_views.xml',
    ],
    'images': ["static/description/banner.png"],
    'installable': True,
    'application': False,
}
