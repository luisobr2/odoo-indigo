# -*- coding: utf-8 -*-
from odoo import fields, models


class IndigoDesign(models.Model):
    _name = "indigo.design"
    _description = "Diseno del catalogo Indigo"
    _order = "code"

    code = fields.Char(string="Codigo", required=True, index=True, help="Ej. ID01, TD-SD-W06")
    name = fields.Char(string="Nombre", translate=True)

    # Per-user favourites for the catalog "My Favorites" tab. Stored as
    # M2M to res.users so multiple managers can keep independent
    # shortlists without stomping on each other.
    favorite_user_ids = fields.Many2many(
        "res.users",
        "indigo_design_user_favorite_rel",
        "design_id",
        "user_id",
        string="Favourited by",
    )
    door_type = fields.Selection(
        [
            ("SD", "Single Door"),
            ("DD", "Double Door"),
            ("sidelite", "Door with Sidelites"),
        ],
        string="Tipo de puerta",
    )
    image = fields.Image(string="Imagen", max_width=1024, max_height=1024)
    description = fields.Text(string="Descripcion", translate=True)
    active = fields.Boolean(default=True)

    # ---------- Variation specs ----------
    # These constrain the order-line picker for this design. They're stored
    # as comma-separated codes so we don't need a relational table per axis
    # and any future axis can be added without a schema migration.
    allowed_colors = fields.Char(
        string="Colors available",
        help="Comma-separated list of color codes (white,bronze,black,custom). "
             "Empty = all defaults from indigo.order.line are allowed.",
    )
    allowed_glass_types = fields.Char(
        string="Glass types available",
        help="Comma-separated glass-type tokens (e.g. ESW,CGI,Tempered). "
             "Empty = free-form glass type.",
    )
    allowed_brand_ids = fields.Many2many(
        "indigo.brand",
        "indigo_design_brand_rel",
        "design_id",
        "brand_id",
        string="Compatible brands",
        help="Restrict the brand picker to these on order lines using this "
             "design. Empty = any brand is allowed.",
    )
    min_width = fields.Float(string="Min width (in)", digits=(8, 3))
    max_width = fields.Float(string="Max width (in)", digits=(8, 3))
    min_height = fields.Float(string="Min height (in)", digits=(8, 3))
    max_height = fields.Float(string="Max height (in)", digits=(8, 3))

    _sql_constraints = [
        ("code_uniq", "unique(code)", "El codigo del diseno debe ser unico."),
    ]
