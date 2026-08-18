# -*- coding: utf-8 -*-
"""Storefront family consolidation: one published card per design family.

Staff add a new door as separate Single + Double products and publish both;
the automation (ProductTemplate.create/write -> _indigo_reconcile_family) must
keep only ONE published card per family, leaving the sibling unpublished but
still orderable via the type selector.

Which one stays is the flexible member (CUSTOM-like, no fixed type) if the
family has one, else the SINGLE -- priority SD > DD > SDL, see
_INDIGO_TYPE_PRIORITY in models/indigo_sale_bridge.py. Single is primary
because the card links to its own PDP and the shop defaults to the Single
filter, so the detail page has to open on Single and let the selector switch
to Double.

That was not always so: until 9b9395e (2026-07-13) the Double was primary,
and the two tests below kept asserting the Double for a month after the
change -- the only reason this suite had two red tests. They now assert the
current contract.
"""
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indigo_family")
class TestIndigoShopFamily(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Design = cls.env["indigo.design"]
        cls.Tmpl = cls.env["product.template"]

    def _make(self, name, code, door_type, published=True, skip=False):
        """Create an Indigo-design product linked to a (code, door_type) design.

        door_type=False makes it a flexible member (no fixed type), like CUSTOM.
        The template's own indigo_door_type is left unset so the effective type
        comes from the design — mirroring how staff actually add them.
        skip=True creates it with indigo_skip_reconcile so the automation does
        not fire (used to set up a specific pre-reconcile family state).
        """
        design = self.Design.create({
            "code": code,
            "name": name,
            "door_type": door_type or False,
        })
        Tmpl = self.Tmpl.with_context(indigo_skip_reconcile=True) if skip else self.Tmpl
        return Tmpl.create({
            "name": name,
            "is_indigo_design": True,
            "indigo_design_id": design.id,
            "is_published": published,
        })

    def test_publishing_both_keeps_only_the_single(self):
        sd = self._make("ZTESTA Single", "ZTESTA-SD", "SD")
        dd = self._make("ZTESTA Double", "ZTESTA-DD", "DD")
        self.assertTrue(sd.is_published, "the Single must remain the family card")
        self.assertFalse(dd.is_published, "the Double sibling must be unpublished")
        # the kept card's own type field is filled in for consistency
        self.assertEqual(sd.indigo_door_type, "SD")
        # the type filter still sees both types available in the family
        self.assertEqual(set((sd.indigo_avail_types or "").split(",")), {"SD", "DD"})

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
        # The reconcile has to fire on write, not only on create -- staff
        # routinely publish the second sibling days later.
        sd = self._make("ZTESTD Single", "ZTESTD-SD", "SD", published=True)
        dd = self._make("ZTESTD Double", "ZTESTD-DD", "DD", published=False)
        self.assertTrue(sd.is_published)
        dd.is_published = True  # staff publishes the Double afterwards
        self.assertTrue(sd.is_published, "the Single stays the family card")
        self.assertFalse(
            dd.is_published,
            "publishing the Double must fold it back under the Single card",
        )

    def test_unpublished_draft_is_never_resurrected(self):
        # Two working cards published (SD + SDL) and a Double left unpublished
        # as a draft. Reconcile must keep one of the PUBLISHED cards and must
        # NOT force-publish the draft Double nor hide both working cards.
        sd = self._make("ZTESTF Single", "ZTESTF-SD", "SD",
                        published=True, skip=True)
        sdl = self._make("ZTESTF Sidelite", "ZTESTF-SDL", "sidelite",
                         published=True, skip=True)
        dd = self._make("ZTESTF Double", "ZTESTF-DD", "DD",
                        published=False, skip=True)
        # Trigger reconcile from a CLEAN context — the skip flag rides on the
        # records created above, so call through a fresh recordset.
        self.Tmpl.browse(sd.id)._indigo_reconcile_family()
        (sd | sdl | dd).invalidate_recordset()  # reconcile wrote in another env
        self.assertFalse(dd.is_published, "a deliberately-unpublished draft must stay hidden")
        pubs = (sd | sdl | dd).filtered("is_published")
        self.assertEqual(len(pubs), 1, "exactly one card stays published")
        self.assertEqual(pubs, sd, "the best-priority PUBLISHED card (SD) is kept")

    def test_single_family_gets_avail_types(self):
        # A brand-new single-member design must get its type-filter string set
        # (else it silently drops out of /shop?type=SD until a manual recompute).
        sd = self._make("ZTESTG Single", "ZTESTG-SD", "SD")
        sd.invalidate_recordset()  # avail_types written inside reconcile's env
        self.assertEqual(sd.indigo_avail_types, "SD")

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
