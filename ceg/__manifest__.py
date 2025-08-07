# -*- coding: utf-8 -*-
{
    'name': "CEG",
    'version': '18.0.0.4',

    'summary': """
        Modulo para customizaciones de CEG
    """,

    'description': """    """,

    'author': "Chroma",
    'website': "https://portal.chroma.agency/",
    'maintainer': 'Chroma',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Account',
    # any module necessary for this one to work correctly
    'depends': ['whatsapp', 'odoo_magento2_ept', 'purchase', 'sale', 'sale_purchase', 'auth_api_key', 'l10n_mx_edi'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_advance_payment_inv_views.xml',
        'views/purchase_order_views.xml',
        'views/magento_status_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': True,

}

