{
    'name': 'Custom Commission Management',
    'version': '1.0',
    'summary': 'Commission calculation and purchase order creation for sales deals',
    'description': 'Automatically calculates commissions and creates purchase orders for employees after a deal is closed.',
    'category': 'Sales',
    'author': 'Your Name',
    'depends': ['sale', 'purchase', 'account'],
    'data': [
        'views/sale_order.xml',
        'views/purchase_order.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
