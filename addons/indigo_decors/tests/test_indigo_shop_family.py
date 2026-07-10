# -*- coding: utf-8 -*-
"""Storefront family consolidation: one published card per design family.

Staff add a new door as separate Single + Double products and publish both;
the automation (ProductTemplate.create/write -> _indigo_reconcile_family) must
keep only ONE published card per family (the Double, or a flexible member),
leaving the sibling unpublished but still orderable via the type selector.
"""
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indigo_family")
class TestIndigoShopFamily(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Design = cls.env["indigo.design"]
        cls.Tmpl = cls.env["product.template"]

    def _make(self, name, code, door_type, published=True):
        """Create an Indigo-design product linked to a (code, door_type) design.

        door_type=False makes it a flexible member (no fixed type), like CUSTOM.
        The template's own indigo_door_type is left unset so the effective type
        comes from the design — mirroring how staff actually add them.
        """
        design = self.Design.create({
            "code": code,
            "name": name,
            "door_type": door_type or False,
        })
        return self.Tmpl.create({
            "name": name,
            "is_indigo_design": True,
            "indigo_design_id": design.id,
            "is_published": published,
        })

    def test_publishing_both_keeps_only_the_double(self):
        sd = self._make("ZTESTA Single", "ZTESTA-SD", "SD")
        dd = self._make("ZTESTA Double", "ZTESTA-DD", "DD")
        self.assertFalse(sd.is_published, "the Single sibling must be unpublished")
        self.assertTrue(dd.is_published, "the Double must remain the family card")
        # the kept card's own type field is filled in for consistency
        self.assertEqual(dd.indigo_door_type, "DD")
        # the type filter still sees both types available in the family
        self.assertEqual(set((dd.indigo_avail_types or "").split(",")), {"SD", "DD"})

    def test_single_only_stays_published(self):
        sd = self._make("ZTESTB Single", "ZTESTB-SD", "SD")
        self.assertTrue(
            sd.is_published,
            "a family with a single card must not be touched (no forced Double)",
        )

    def test_flexible_member_wins_over_double(self):
        flex = self._make("ZTESTC", "ZTESTC", False)          # flexible (CUSTOM-like)
        dd = self._make("ZTESTC Double", "ZTESTC-DD", "DD")
        self.assertTrue(flex.is_published, "the flexible member is the family card")
        self.assertFalse(dd.is_published, "the fixed Double is unpublished under a flexible card")

    def test_publish_later_reconciles_via_write(self):
        sd = self._make("ZTESTD Single", "ZTESTD-SD", "SD", published=True)
        dd = self._make("ZTESTD Double", "ZTESTD-DD", "DD", published=False)
        self.assertTrue(sd.is_published)
        dd.is_published = True  # staff publishes the Double afterwards
        self.assertFalse(sd.is_published, "publishing the Double must unpublish the Single")
        self.assertTrue(dd.is_published)

    def test_skip_context_bypasses_reconcile(self):
        sd = self._make("ZTESTE Single", "ZTESTE-SD", "SD")
        dd = self.Tmpl.with_context(indigo_skip_reconcile=True).create({
            "name": "ZTESTE Double",
            "is_indigo_design": True,
            "indigo_design_id": self.Design.create(
                {"code": "ZTESTE-DD", "name": "ZTESTE Double", "door_type": "DD"}
            ).id,
            "is_published": True,
        })
        self.assertTrue(sd.is_published, "skip context must leave both published")
        self.assertTrue(dd.is_published, "skip context must leave both published")
