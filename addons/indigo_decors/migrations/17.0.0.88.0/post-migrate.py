# -*- coding: utf-8 -*-
"""Post-migration: classify pre-existing on-hold orders as 'other'.

v0.88 adds hold_cause (Selection: dealer/client/other) alongside the old
free-text hold_reason, and the model now REQUIRES a cause whenever on_hold
is true (see indigo.order._check_hold_requires_cause). Orders that were
already on hold before this version have on_hold=true and a free-text
hold_reason but no hold_cause -- if we left them alone they'd fail that new
constraint the moment anyone touched on_hold/hold_cause on them, and worse,
they'd be invisible to the new dealer/client counters on the Installations
screen.

We do NOT try to infer dealer vs client from the free-text hold_reason --
that text was written for a human, not a classifier, and a wrong guess
would silently mislabel a blocked door. Instead every pre-existing on-hold
order is set to hold_cause='other' ("Otro / sin clasificar"), which is a
real, visible, low-cardinality bucket Majela can filter/group on in Odoo
and see surfaced in the panel -- and fix by hand, order by order.

This runs once after the module upgrade to v0.88.0.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE indigo_order
        SET hold_cause = 'other'
        WHERE on_hold = true AND hold_cause IS NULL
    """)
