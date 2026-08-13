# -*- coding: utf-8 -*-
"""Atomic rename of a design family code.

What the operator calls one design (ID60) is 1-3 indigo.design records
(ID60-SD/-DD/-SDL) plus a linked storefront product each. The panel used to
rename them with one RPC per record, so a failure halfway left the family
split across two codes and it stopped grouping in the catalog. rename_family
does the whole cascade inside a single transaction instead: any error aborts
everything.
"""
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indigo_rename")
class TestIndigoDesignRename(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Design = cls.env["indigo.design"]
        cls.Tmpl = cls.env["product.template"]

    def _family(self, family, types=("SD", "DD"), with_products=True):
        """Create a design family (and its storefront products, like the panel)."""
        made = {}
        label = {"SD": "Single Door", "DD": "Double Door", "SDL": "Door with Sidelites"}
        dtype = {"SD": "SD", "DD": "DD", "SDL": "sidelite"}
        for t in types:
            design = self.Design.create({
                "code": "%s-%s" % (family, t),
                "name": "%s %s" % (family, label[t]),
                "door_type": dtype[t],
            })
            if with_products:
                self.Tmpl.with_context(indigo_skip_reconcile=True).create({
                    "name": "%s %s" % (family, label[t]),
                    "is_indigo_design": True,
                    "indigo_design_id": design.id,
                })
            made[t] = design
        return made

    def _codes(self, designs):
        return sorted(d.code for d in designs.values())

    # ---- happy path -------------------------------------------------------

    def test_renames_every_sibling_preserving_suffixes(self):
        fam = self._family("ZREN", ("SD", "DD", "SDL"))
        res = self.Design.rename_family(fam["SD"].id, "ZREN2")

        self.assertEqual(res["next_family"], "ZREN2")
        self.assertEqual(len(res["renamed"]), 3)
        self.assertEqual(self._codes(fam), ["ZREN2-DD", "ZREN2-SD", "ZREN2-SDL"])

    def test_renames_design_and_storefront_product_names(self):
        fam = self._family("ZRENB", ("SD",))
        self.Design.rename_family(fam["SD"].id, "ZRENC")

        self.assertEqual(fam["SD"].name, "ZRENC Single Door")
        prod = self.Tmpl.search([("indigo_design_id", "=", fam["SD"].id)])
        self.assertEqual(prod.name, "ZRENC Single Door")

    def test_normalizes_the_typed_code(self):
        fam = self._family("ZRENN", ("SD",))
        # lowercase, padded, and carrying a door-type suffix the user typed.
        res = self.Design.rename_family(fam["SD"].id, "  zrennx-sd  ")
        self.assertEqual(res["next_family"], "ZRENNX")
        self.assertEqual(fam["SD"].code, "ZRENNX-SD")

    def test_unchanged_code_is_a_noop(self):
        fam = self._family("ZRENO", ("SD",))
        res = self.Design.rename_family(fam["SD"].id, "zreno")
        self.assertEqual(res["renamed"], [])
        self.assertEqual(fam["SD"].code, "ZRENO-SD")

    def test_refreshes_the_storefront_type_list(self):
        fam = self._family("ZRENT", ("SD", "DD"))
        self.Design.rename_family(fam["SD"].id, "ZRENU")
        prods = self.Tmpl.search([("indigo_design_id", "in", [d.id for d in fam.values()])])
        # The family moved wholesale, so both types must still be offered —
        # a stale list here would break the /shop type filter.
        for p in prods:
            self.assertEqual(
                sorted((p.indigo_avail_types or "").split(",")), ["DD", "SD"]
            )

    # ---- refusals ---------------------------------------------------------

    def test_refuses_when_a_target_code_is_taken_and_writes_nothing(self):
        fam = self._family("ZRENP", ("SD", "DD"))
        self._family("ZRENQ", ("DD",))  # ZRENQ-DD already exists

        with self.assertRaises(ValidationError):
            self.Design.rename_family(fam["SD"].id, "ZRENQ")
        # The refusal is pre-flight: nothing may have moved.
        self.assertEqual(self._codes(fam), ["ZRENP-DD", "ZRENP-SD"])

    def test_refuses_a_rename_that_would_merge_two_designs(self):
        fam = self._family("ZRENM", ("SD", "DD"))
        # A standalone design with no door-type suffix. Renaming ZRENM -> ZARCH
        # duplicates NO code (targets are ZARCH-SD/-DD) so the unique
        # constraint stays quiet, but both would group under family ZARCH and
        # merge into one catalog card.
        self.Design.create({"code": "ZARCH", "name": "ZARCH"})

        with self.assertRaises(ValidationError):
            self.Design.rename_family(fam["SD"].id, "ZARCH")
        self.assertEqual(self._codes(fam), ["ZRENM-DD", "ZRENM-SD"])

    def test_refuses_codes_that_would_break_grouping_or_labels(self):
        fam = self._family("ZRENV", ("SD",))
        for bad in ("", "   ", "A", "ZR EN", "ZR/EN", "-SD"):
            with self.assertRaises(ValidationError):
                self.Design.rename_family(fam["SD"].id, bad)
        self.assertEqual(fam["SD"].code, "ZRENV-SD")

    def test_archived_siblings_move_too(self):
        fam = self._family("ZRENA", ("SD", "DD"))
        fam["DD"].active = False

        self.Design.rename_family(fam["SD"].id, "ZRENB2")
        # An archived version keeps its code and would otherwise be orphaned
        # under the old family — and its code would still block reusing it.
        self.assertEqual(self._codes(fam), ["ZRENB2-DD", "ZRENB2-SD"])

    def test_requires_manager_or_office(self):
        fam = self._family("ZRENZ", ("SD",))
        painter = self.env["res.users"].create({
            "name": "ZRen Painter",
            "login": "zren.painter@test.local",
            "groups_id": [(6, 0, [self.env.ref("indigo_decors.group_indigo_painter_op").id])],
        })
        with self.assertRaises(AccessError):
            self.Design.with_user(painter).rename_family(fam["SD"].id, "ZRENY")
        self.assertEqual(fam["SD"].code, "ZRENZ-SD")
