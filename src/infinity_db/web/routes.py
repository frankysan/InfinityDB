"""Shared route identities used by HTTP dispatch, presentation, and metrics."""

from __future__ import annotations

import re
from collections.abc import Collection
from re import Pattern

DOMAIN_ROUTE_IDENTIFIER = r"[a-z0-9]+(?:-[a-z0-9]+)*"

UNIT_PAGE_PATH = re.compile(rf"/units/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
UNIT_API_PATH = re.compile(rf"/api/units/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
SKILL_PAGE_PATH = re.compile(rf"/skills/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
SKILL_API_PATH = re.compile(rf"/api/skills/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
EQUIPMENT_PAGE_PATH = re.compile(
    rf"/equipment/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})"
)
EQUIPMENT_API_PATH = re.compile(
    rf"/api/equipment/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})"
)
WEAPON_PAGE_PATH = re.compile(rf"/weapons/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
WEAPON_API_PATH = re.compile(rf"/api/weapons/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
STATE_PAGE_PATH = re.compile(rf"/states/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
STATE_API_PATH = re.compile(rf"/api/states/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
HACKING_PROGRAM_PAGE_PATH = re.compile(
    rf"/hacking-programs/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})"
)
HACKING_PROGRAM_API_PATH = re.compile(
    rf"/api/hacking-programs/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})"
)
AMMUNITION_PAGE_PATH = re.compile(
    rf"/ammunition/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})"
)
AMMUNITION_API_PATH = re.compile(
    rf"/api/ammunition/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})"
)
LABEL_PAGE_PATH = re.compile(rf"/labels/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
LABEL_API_PATH = re.compile(rf"/api/labels/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
TRAIT_PAGE_PATH = re.compile(rf"/traits/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")
TRAIT_API_PATH = re.compile(rf"/api/traits/(?P<identifier>{DOMAIN_ROUTE_IDENTIFIER})")

ARMY_SYMBOL_PATH = re.compile(r"/static/armies/[a-z0-9-]+/[a-z0-9-]+\.svg")
UNIT_SYMBOL_PATH = re.compile(r"/static/units/[a-z0-9-]+/[a-z0-9-]+\.svg")
ORDER_SYMBOL_PATH = re.compile(
    r"/static/orders/(regular|irregular|impetuous|tactical|lieutenant)\.svg"
)
CHARACTERISTIC_SYMBOL_PATH = re.compile(
    r"/static/characteristics/(peripheral|hackable|cube|cube-2)\.svg"
)

_METRIC_FIXED_PATHS = frozenset(
    {
        "/",
        "/about",
        "/armies",
        "/units",
        "/skills",
        "/equipment",
        "/weapons",
        "/traits",
        "/states",
        "/hacking-programs",
        "/ammunition",
        "/labels",
        "/skill-extras",
        "/fireteams",
        "/search",
        "/api/version",
        "/api/armies",
        "/api/units",
        "/api/visible-unit-ids",
        "/api/skills",
        "/api/equipment",
        "/api/weapons",
        "/api/traits",
        "/api/states",
        "/api/hacking-programs",
        "/api/ammunition",
        "/api/labels",
        "/api/skill-extras",
        "/api/unit-profile-help",
        "/api/fireteams",
        "/api/search",
    }
)
_METRIC_PARAMETERIZED_PATHS: tuple[tuple[Pattern[str], str], ...] = (
    (UNIT_PAGE_PATH, "/units/:id"),
    (SKILL_PAGE_PATH, "/skills/:id"),
    (EQUIPMENT_PAGE_PATH, "/equipment/:id"),
    (WEAPON_PAGE_PATH, "/weapons/:id"),
    (TRAIT_PAGE_PATH, "/traits/:id"),
    (STATE_PAGE_PATH, "/states/:id"),
    (HACKING_PROGRAM_PAGE_PATH, "/hacking-programs/:id"),
    (AMMUNITION_PAGE_PATH, "/ammunition/:id"),
    (LABEL_PAGE_PATH, "/labels/:id"),
    (UNIT_API_PATH, "/api/units/:id"),
    (SKILL_API_PATH, "/api/skills/:id"),
    (EQUIPMENT_API_PATH, "/api/equipment/:id"),
    (WEAPON_API_PATH, "/api/weapons/:id"),
    (TRAIT_API_PATH, "/api/traits/:id"),
    (STATE_API_PATH, "/api/states/:id"),
    (HACKING_PROGRAM_API_PATH, "/api/hacking-programs/:id"),
    (AMMUNITION_API_PATH, "/api/ammunition/:id"),
    (LABEL_API_PATH, "/api/labels/:id"),
)
_SYMBOL_PATHS = (
    ARMY_SYMBOL_PATH,
    UNIT_SYMBOL_PATH,
    ORDER_SYMBOL_PATH,
    CHARACTERISTIC_SYMBOL_PATH,
)


def metric_route(path: str, static_asset_paths: Collection[str]) -> str:
    """Normalize one request path to the fixed observability route vocabulary."""

    if path in _METRIC_FIXED_PATHS:
        return path
    for pattern, normalized in _METRIC_PARAMETERIZED_PATHS:
        if pattern.fullmatch(path):
            return normalized
    if path in static_asset_paths:
        return "/static/:asset"
    if any(pattern.fullmatch(path) for pattern in _SYMBOL_PATHS):
        return "/static/:symbol"
    return "/other"
