# -*- coding: utf-8 -*-
{
    'name': "Developer Helper",

    'summary': """
        Helps you get to the technical data faster and easier.
    """,

    'description': """
        Helps you get to the technical data faster and easier.
    """,

    'author': 'Rama Altayeb',
    'website': 'https://ramaaltayeb.github.io',
    'category': 'Extra Tools',
    'version': '17.0.0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'views/ir_actions_report.xml',
        'views/ir_actions_server.xml',
        'views/ir_filters.xml',
        'views/ir_model_access.xml',
        'views/ir_model_fields.xml',
        'views/ir_model.xml',
        'views/ir_rule.xml',
        'views/ir_sequence.xml',
        'views/ir_ui_menu.xml',
        'views/report_paperformat.xml',
        'views/res_groups.xml',
    ],

    'images': [
        'static/description/banner.png',
    ]
}
