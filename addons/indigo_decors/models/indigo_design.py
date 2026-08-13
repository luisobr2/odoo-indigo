# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

# Same rule as product.template._indigo_family_code and the panel's
# /api/catalog/designs/families: strip a trailing door-type suffix only when a
# real code is left in front, so two unrelated short codes never collapse into
# one family. Keep the three in sync.
_SUFFIX_RE = re.compile(r"^(.+)-(SD|DD|SDL)$", re.I)

# Codes end up on printed labels, QR payloads and attachment filenames, so keep
# them to the characters that survive all three.
_VALID_FAMILY_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")


def _family_of(code):
    code = (code or "").strip().upper()
    m = _SUFFIX_RE.match(code)
    if m and len(m.group(1)) >= 2:
        return m.group(1)
    return code


def _rename_prefix(text, family, target):
    """Swap the family prefix at the START of a display name, followed by a
    boundary — so "ID60 Single Door" moves but "Puerta tipo ID60" and
    "ID601 Single Door" are left alone."""
    if not text:
        return text
    return re.sub(
        r"^%s(?=$|[\s-])" % re.escape(family), target, text, count=1, flags=re.I
    )


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

    # ---------- Catalog origin ----------
    # Marks which catalog a design comes from. Lets the operator filter
    # /catalog by source ("show me only Indigo" vs "show me Lock Tight")
    # and lets reports break down usage by catalog.
    #
    # Existing designs default to 'indigo' (the original Indigo Decors
    # catalogue ID01.. ID34). CUSTOM-SD/CUSTOM-DD get retro-tagged to
    # 'custom'. Lock Tight imports get tagged 'locktight'.
    catalog_source = fields.Selection(
        [
            ('indigo', 'Indigo Decors'),
            ('locktight', 'Lock Tight'),
            ('custom', 'Custom (dealer photo)'),
            ('other', 'Other dealer'),
        ],
        string="Catalog source",
        default='indigo',
        index=True,
        help="Where this design comes from. Used to filter the catalog grid "
             "and to break down design usage in reports.",
    )

    # ---------- Per-design price override ----------
    # Prices are normally by door type ($300 single / $600 double, from the
    # base matrix). This lets a SPECIFIC design carry its own price instead:
    # when > 0 the catalog shows it and new order lines bill it (as a custom
    # line). 0 / empty = use the base price for the door type.
    dealer_price_override = fields.Float(
        string="Own price (USD)",
        digits=(10, 2),
        default=0.0,
        help="Optional. Special price for THIS design, overriding the base "
             "price for its door type. Leave empty to use the base price.",
    )

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

    # ---------- Family rename (single transaction) ----------
    @api.model
    def rename_family(self, design_id, next_family):
        """Rename a whole design family in ONE transaction.

        A design the operator sees as `ID60` is 1-3 records (ID60-SD/-DD/-SDL)
        plus a linked storefront product each. Renaming them one RPC at a time
        can fail halfway and leave the family split across two codes, which
        stops it grouping in the catalog. Doing it here means any error aborts
        the whole thing.

        Called by the Next.js panel as the logged-in user. Office staff have
        write on indigo.design but not on product.template, so the storefront
        half runs sudo() after the role check.

        Returns {'family', 'next_family', 'renamed': [{id, from, to}],
                 'products_renamed'}.
        """
        user = self.env.user
        if not (
            user._is_admin()
            or user.has_group("indigo_decors.group_indigo_manager")
            or user.has_group("indigo_decors.group_indigo_office")
        ):
            raise AccessError(_("Only Indigo managers or office staff can rename a design."))

        anchor = self.with_context(active_test=False).browse(int(design_id)).exists()
        if not anchor:
            raise ValidationError(_("Design not found."))

        family = _family_of(anchor.code)
        target = _family_of(next_family or "")
        if not target:
            raise ValidationError(_("Enter a code."))
        if len(target) < 2:
            raise ValidationError(_("The code needs at least 2 characters."))
        if not _VALID_FAMILY_RE.match(target):
            raise ValidationError(
                _("Use only letters, numbers, hyphen or underscore — no spaces or slashes.")
            )
        if target == family:
            return {
                "family": family,
                "next_family": target,
                "renamed": [],
                "products_renamed": 0,
            }

        # Archived designs are included on purpose: they keep their code (the
        # unique constraint covers them too), so they both move with the family
        # and can block the target.
        every = self.with_context(active_test=False).search([])
        siblings = every.filtered(lambda d: _family_of(d.code) == family)
        if not siblings:
            raise ValidationError(_("No versions of this design were found to rename."))

        # Refuse if the target FAMILY is occupied — a duplicate-code check is
        # not enough. Renaming ID60 -> ARCH when a standalone `ARCH` exists
        # duplicates no code (targets are ARCH-SD/-DD), so the unique
        # constraint stays quiet, yet both group under family ARCH and the two
        # designs merge into a single catalog card.
        own = {(d.code or "").strip().upper() for d in siblings}
        conflicts = sorted(
            {
                (d.code or "").strip().upper()
                for d in every
                if (d.code or "").strip().upper() not in own
                and _family_of(d.code) == target
            }
        )
        if conflicts:
            archived = sorted(
                {
                    (d.code or "").strip().upper()
                    for d in every
                    if not d.active and (d.code or "").strip().upper() in conflicts
                }
            )
            msg = _(
                "A design is already using %(target)s (%(codes)s). Pick a different code.",
                target=target,
                codes=", ".join(conflicts),
            )
            if archived:
                # Otherwise the operator hunts for a design that isn't on screen.
                msg += " " + _(
                    "Note: %(codes)s belongs to an archived design — it does not show "
                    "in the catalog, but the code is still taken.",
                    codes=", ".join(archived),
                )
            raise ValidationError(msg)

        renamed = []
        for design in siblings:
            code = (design.code or "").strip().upper()
            m = _SUFFIX_RE.match(code)
            if m and len(m.group(1)) >= 2:
                new_code = "%s-%s" % (target, m.group(2).upper())
            else:
                new_code = target
            vals = {"code": new_code}
            if design.name:
                vals["name"] = _rename_prefix(design.name, family, target)
            old_code = design.code
            design.write(vals)
            renamed.append({"id": design.id, "from": old_code, "to": new_code})

        # Storefront half. The product name carries the code, and the cached
        # door-type list is keyed on the design code (see
        # product.template._indigo_family_code), so it has to be recomputed —
        # it is a plain stored field, not an automatic compute.
        products = self.env["product.template"].sudo().search(
            [("indigo_design_id", "in", siblings.ids)]
        )
        products_renamed = 0
        for tmpl in products:
            nxt = _rename_prefix(tmpl.name or "", family, target)
            if nxt != (tmpl.name or ""):
                tmpl.write({"name": nxt})
                products_renamed += 1
        if products:
            products.with_context(indigo_skip_reconcile=True)._indigo_compute_avail_types()

        return {
            "family": family,
            "next_family": target,
            "renamed": renamed,
            "products_renamed": products_renamed,
        }
