# -*- coding: utf-8 -*-
{
    'name': 'Indigo Decors',
    'version': '17.0.0.4.0',
    'category': 'Manufacturing',
    'summary': 'Gestion de ordenes de puertas decorativas',
    'description': """
Indigo Decors — Gestion de ordenes
==================================
Modulo a medida para el taller Indigo Decors:
ordenes multi-pieza, pipeline kanban configurable por dealer,
documentos (ficha de orden, etiqueta del disenador, hoja del pintor),
liquidacion de contratistas (pintor por SQF, instaladores por puerta)
y portal externo para instaladores.
""",
    'author': 'Indigo Decors',
    'website': 'https://www.indigodecors.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
        'product',
        'account',
        'portal',
    ],
    'data': [
        'security/indigo_security.xml',
        'security/ir.model.access.csv',
        'data/indigo_sequence.xml',
        'data/indigo_stages.xml',
        'data/mail_templates.xml',
        'views/indigo_stage_views.xml',
        'views/indigo_design_views.xml',
        'views/indigo_dealer_views.xml',
        'views/indigo_order_views.xml',
        'views/indigo_order_kanban.xml',
        'views/indigo_menus.xml',
        'reports/paperformats.xml',
        'reports/order_card_report.xml',
        'reports/order_label_report.xml',
        'reports/painter_sheet_report.xml',
        'reports/installation_addresses_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
