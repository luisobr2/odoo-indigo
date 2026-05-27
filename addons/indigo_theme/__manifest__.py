# -*- coding: utf-8 -*-
{
    'name': 'Indigo Theme',
    'version': '17.0.2.0.0',
    'category': 'Theme/eCommerce',
    'summary': 'Theme IKEA-inspired para Indigo Decors — Noto Sans, paleta indigo, pill buttons',
    'description': 'Theme profesional con arquitectura correcta Odoo 17: '
                   'primary_variables.scss prepended, theme.utils post_copy, '
                   'mirror models (theme.website.page) y CSS fallback via <link>.',
    'author': 'Indigo Decors',
    'website': 'https://www.indigodecors.com',
    'support': 'sales@indigodecors.com',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'indigo_decors',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/layout/templates.xml',
        'views/snippets/catalog_header_snippet.xml',
        'views/product_detail.xml',
        'views/checkout_address.xml',
        'data/pages/home_page.xml',
        'data/pages/dealer_program_page.xml',
        'data/pages/about_page.xml',
        'data/pages/gallery_page.xml',
        'data/website_settings.xml',
    ],
    'assets': {
        # Solo frontend - no tocar _assets_primary_variables (rompia el backend)
        'web.assets_frontend': [
            'indigo_theme/static/src/scss/theme.scss',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
