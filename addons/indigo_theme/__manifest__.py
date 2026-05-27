# -*- coding: utf-8 -*-
{
    'name': 'Indigo Theme',
    'description': 'Theme custom para Indigo Decors — estilo limpio, profesional, '
                   'inspirado en IKEA. Tipografia Noto Sans, paleta azul Indigo, '
                   'cards rounded-3xl, pill buttons, white space generoso.',
    'category': 'Theme/eCommerce',
    'version': '17.0.1.0.0',
    'author': 'Indigo Decors',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'indigo_decors',  # Para que reutilice tarifas, dealer flags, etc.
    ],
    'data': [
        'views/layout.xml',
        'views/footer.xml',
        'views/homepage.xml',
        'views/shop.xml',
        'views/product.xml',
        'data/website_settings.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'indigo_theme/static/src/scss/variables.scss',
        ],
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
