"""Curated N5 skill declaration categories.

The Infinity Army snapshot identifies skills but does not include their
declaration categories.  This mapping supplements that snapshot with the N5
v5.3 rules reference (``eng-n5-update-5-3.pdf``), cited by its printed page.
It deliberately permits more than one category: for example, Dodge is both a
Basic Short Skill and an ARO.
"""

from __future__ import annotations


UNCLASSIFIED = "Unclassified"

# Categories are the declaration labels printed for the skill.  The page
# numbers are printed page numbers in eng-n5-update-5-3.pdf, not PDF indexes.
# IDs are used because the Army data contains display-name variants.
SKILL_CATEGORIES: dict[int, tuple[tuple[str, int], ...]] = {
    19: (("Automatic", 100),), 20: (("Automatic", 100),),
    21: (("Automatic", 100),), 22: (("Automatic", 100),),
    23: (("Automatic", 100),), 24: (("Entire Order", 86),),
    25: (("Automatic", 87),), 26: (("Automatic", 90),),
    28: (("Automatic", 102),), 29: (("Automatic", 87),),
    33: (("Deployment", 89),), 35: (("Long Skill", 89),),
    38: (("Automatic", 92),), 39: (("Automatic", 101),),
    40: (("Basic Short Skill", 79), ("ARO", 79)),
    47: (("Deployment", 89),), 49: (("Basic Short Skill", 91), ("ARO", 91)),
    52: (("Automatic", 99),), 53: (("Basic Short Skill", 90), ("ARO", 90)),
    55: (("Automatic", 98),), 56: (("Deployment", 102),),
    58: (("Automatic", 118),), 59: (("Basic Short Skill", 92), ("ARO", 92)),
    61: (("Automatic", 118),), 62: (("Automatic", 116),),
    64: (("Basic Short Skill", 105), ("ARO", 105)),
    65: (("Basic Short Skill", 112), ("ARO", 112)), 67: (("Automatic", 112),),
    69: (("Automatic", 113),), 70: (("Automatic", 113),),
    72: (("Automatic", 109),), 73: (("Basic Short Skill", 103), ("ARO", 103)),
    74: (("Automatic", 114),), 82: (("Automatic", 88),),
    83: (("Automatic", 110),), 84: (("Automatic", 90),),
    85: (("Automatic", 91),), 86: (("Automatic", 91),),
    89: (("Deployment", 111), ("Long Skill", 111)),
    1000: (("Automatic", 95),), 109: (("Automatic", 104),),
    119: (("Automatic", 113),), 122: (("Automatic", 105),),
    131: (("Basic Short Skill", 78), ("ARO", 78)), 156: (("Automatic", 100),),
    161: (("Deployment", 92),), 162: (("Automatic", 96),),
    164: (("Automatic", 112),), 189: (("Automatic", 112),),
    191: (("Automatic", 88),), 201: (("Basic Short Skill", 40), ("ARO", 40)),
    207: (("Automatic", 90),), 211: (("Automatic", 104),),
    213: (("Automatic", 115),), 215: (("Automatic", 89),),
    220: (("Automatic", 118),), 235: (("Automatic", 102),),
    237: (("Automatic", 111),), 238: (("Deployment", 94),),
    240: (("Basic Short Skill", 45), ("ARO", 45)),
    242: (("Basic Short Skill", 118), ("ARO", 118)), 243: (("Automatic", 106),),
    246: (("Automatic", 117),), 247: (("Automatic", 95),),
    248: (("Automatic", 103),), 249: (("Deployment", 93),),
    250: (("Automatic", 93),), 251: (("Automatic", 112),),
    252: (("Automatic", 94),), 254: (("Basic Short Skill", 86), ("ARO", 86)),
    255: (("Automatic", 110),), 256: (("Automatic", 97),),
    258: (("Automatic", 93),), 259: (("Automatic", 92),),
    260: ((UNCLASSIFIED, 0),), 261: (("Automatic", 93),),
    262: (("Automatic", 88),), 263: (("Long Skill", 25),),
    264: ((UNCLASSIFIED, 0),), 265: (("Automatic", 86),),
    266: ((UNCLASSIFIED, 0),), 267: (("Automatic", 118),),
    268: (("Automatic", 100),), 270: (("Automatic", 115),),
    271: (("Long Skill", 25),), 272: (("Automatic", 99),),
    273: (("Basic Short Skill", 91), ("ARO", 91)),
    274: ((UNCLASSIFIED, 0),), 275: (("Automatic", 115),),
    276: (("Automatic", 116),), 277: (("Basic Short Skill", 90), ("ARO", 90)),
    278: ((UNCLASSIFIED, 0),), 279: ((UNCLASSIFIED, 0),),
    280: ((UNCLASSIFIED, 0),), 281: (("Automatic", 98),),
    282: ((UNCLASSIFIED, 0),),
}


def categories_for_skill(skill_id: int) -> list[dict[str, int | str | None]]:
    """Return categories and their N5 v5.3 printed-page citations."""
    if skill_id not in SKILL_CATEGORIES:
        return [{"name": UNCLASSIFIED, "source": None, "page": None}]
    return [
        (
            {"name": name, "source": "N5 Core Rules v5.3", "page": page}
            if page
            else {"name": name, "source": None, "page": None}
        )
        for name, page in SKILL_CATEGORIES[skill_id]
    ]
