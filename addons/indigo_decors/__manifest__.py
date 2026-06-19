# -*- coding: utf-8 -*-
{
    'name': 'Indigo Decors',
    'version': '17.0.0.59.0',
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
        'sale_management',
        'website_sale',
    ],
    'data': [
        'security/indigo_security.xml',
        'security/ir.model.access.csv',
        'security/indigo_portal_rules.xml',
        'security/indigo_role_rules.xml',
        'data/indigo_sequence.xml',
        'data/indigo_stages.xml',
        'data/mail_templates.xml',
        'data/demo_dealers.xml',
        # demo_designs.xml / demo_custom_design.xml removed from the load list:
        # the design catalog is now managed via the image import (scripts), and
        # re-seeding these on every -u collided with the imported designs
        # (duplicate indigo_design code) and rolled back the whole upgrade —
        # which silently blocked new column creation. Keep the files in the repo
        # for reference but do NOT load them.
        'data/indigo_brands.xml',
        'data/install_zones.xml',
        'data/design_prices.xml',
        'data/demo_rates.xml',
        'data/demo_direct_sales.xml',
        'data/cron_sla.xml',
        'data/cron_stock.xml',
        'views/indigo_menu_root.xml',
        'views/indigo_stage_views.xml',
        'views/indigo_install_zone_views.xml',
        'views/indigo_design_price_views.xml',
        'views/indigo_design_views.xml',
        'views/indigo_dealer_views.xml',
        # Wizards load BEFORE order_views so the form can reference wizard actions.
        'wizards/indigo_order_bulk_assign_wizard_views.xml',
        'wizards/indigo_payout_settle_wizard_views.xml',
        'wizards/indigo_installation_schedule_wizard_views.xml',
        'wizards/indigo_measurement_entry_wizard_views.xml',
        'wizards/indigo_stage_wizards_views.xml',
        'views/indigo_order_views.xml',
        'views/indigo_order_kanban.xml',
        'views/indigo_order_calendar.xml',
        'views/indigo_payout_views.xml',
        'views/indigo_contractor_rate_views.xml',
        'views/indigo_stock_views.xml',
        'views/product_template_indigo_views.xml',
        'views/sale_order_views.xml',
        'views/indigo_menus.xml',
        'views/portal_templates.xml',
        'views/hide_brand_promotion.xml',
        'reports/paperformats.xml',
        'reports/order_card_report.xml',
        'reports/order_label_report.xml',
        'reports/painter_sheet_report.xml',
        'reports/installation_addresses_report.xml',
        'reports/payout_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'indigo_decors/static/src/js/installation_calendar_patch.js',
            'indigo_decors/static/src/js/dashboard.js',
            'indigo_decors/static/src/xml/dashboard.xml',
            'indigo_decors/static/src/css/dashboard.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    # i18n: fuente es_ES, traduccion ingles en i18n/en.po (parcial ~50%).
}
