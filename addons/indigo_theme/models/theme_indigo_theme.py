# -*- coding: utf-8 -*-
from odoo import models


class ThemeIndigoTheme(models.AbstractModel):
    """Activacion automatica del theme al instalar sobre un website.

    El metodo `_theme_indigo_theme_post_copy` se invoca por Odoo automaticamente
    cuando el theme se aplica a un website (`theme.utils` hook).
    """
    _inherit = 'theme.utils'

    def _theme_indigo_theme_post_copy(self, mod):
        # Header limpio default (no custom header.xml para evitar romper layouts)
        self.enable_view('website.template_header_default')

        # Logo en lugar de brand name
        self.enable_view('website.option_header_brand_logo')
        self.disable_view('website.option_header_brand_name')

        # Footer minimo (lo enriquecemos con snippets indigo)
        self.enable_view('website.template_footer_minimalist')
