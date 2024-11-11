# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MyFatoorah Payment Gateway',
    'category': 'Accounting/Payment Acquirers',
    'version': '2.0',
    'sequence': 1,
    'sequence': 1,
    'Summary': "MyFatoorah Payment Gateway.",
    'description': "A hassle-free payment experience with the international credit cards & local GCC payment methods.",
    'depends': ['payment', 'account', 'website', 'website_sale'],
    'author': "MyFatoorah",
    'company': 'MyFatoorah',
    'maintainer': 'MyFatoorah',
    'website': "https://www.myfatoorah.com",
    'data': [
        'views/direct_template.xml',
        'views/payment_provider.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'myfatoorah_gateway/static/src/js/**/*',
            'myfatoorah_gateway/static/src/css/style.css',
        ],
    },
    'images': ['static/description/main_screenshot.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
