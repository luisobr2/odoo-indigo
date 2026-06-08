# -*- coding: utf-8 -*-
"""Post-migration: backfill glass_privacy from the old is_privacy_glass bool.

Before v0.37 we had a Boolean 'is_privacy_glass'. v0.37 turns it into a
computed field driven by a new Selection 'glass_privacy'. Existing rows
need their selection set from the old boolean values BEFORE the compute
takes over — otherwise everything defaults to 'clear' and we lose history.

This runs once after the module upgrade to v0.37.0.
"""


def migrate(cr, version):
    if not version:
        return
    # Copy old boolean -> new selection, only on rows that haven't been
    # touched yet (default would be 'clear' anyway).
    cr.execute("""
        UPDATE indigo_order_line
        SET glass_privacy = CASE
            WHEN is_privacy_glass THEN 'privacy'
            ELSE 'clear'
        END
        WHERE glass_privacy IS NULL OR glass_privacy = 'clear'
    """)
