# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) PySquad Informetics (<https://www.pysquad.com/>).
#
#    For Module Support : contact@pysquad.com
#
##############################################################################

{
    # Module Information
    "name": "Dynamic Report",
    "version": "17.0.1.0.0",
    "category": "custom",
    "description": "Export to pdf and xls in one click",
    "summary": """
            Dynamic Report
            Export Tree View PDF
            Export Tree View XLSx 
            Creating Fully Dynamically Pdf & XLS report.
            """,

    # Author
    "author": "Pysquad Informatics LLP",
    "website": "https://www.pysquad.com",
    "license": "LGPL-3",

    # Dependencies
    "depends": ["base"],

    # Data File
    "data": [
        'security/ir.model.access.csv',
        'report/dynamic_report.xml',
        'views/dynamic_report_configure.xml',
    ],
    'images': [
        'static/description/banner_img.png',
    ],

    # Technical Specif.
    'installable': True,
    'application': False,
    'auto_install': False,
}
