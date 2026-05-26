# -*- coding: utf-8 -*-
{
    'name': 'Indigo Decors',
    'version': '17.0.0.1.0',
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
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
