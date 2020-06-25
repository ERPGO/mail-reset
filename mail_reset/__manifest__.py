# -*- coding: utf-8 -*-
{
    'name': "Mail Reset app by ERPGO",

    'summary': """
        With this module we are able to reset mail 
        passwords of users for Postfix virtual users.""",

    'description': """
        With this module we are able to reset mail 
        passwords of users for Postfix virtual users.
    """,

    'author': "ERPGO",
    'website': "https://erpgo.az",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
#         'security/ir.model.access.csv',
        'views/reset_submit_form.xml',
        'views/reset_users.xml',
        'views/reset_domain.xml',
        'views/reset_aliases.xml',
        'data/mail_users_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
