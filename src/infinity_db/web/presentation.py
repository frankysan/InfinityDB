"""Shared browser page shell and packaged static-asset delivery."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from html import escape
from http import HTTPStatus
from importlib.resources import files
from urllib.parse import parse_qs

from infinity_army_data.project_resources import maintained_manifest_path
from infinity_db import __display_version__, __version__
from infinity_db.application_domains import application_domain
from infinity_db.web.response import WebResponse
from infinity_db.web.routes import (
    AMMUNITION_PAGE_PATH,
    ARMY_SYMBOL_PATH,
    CHARACTERISTIC_SYMBOL_PATH,
    EQUIPMENT_PAGE_PATH,
    HACKING_PROGRAM_PAGE_PATH,
    LABEL_PAGE_PATH,
    ORDER_SYMBOL_PATH,
    SKILL_PAGE_PATH,
    STATE_PAGE_PATH,
    TRAIT_PAGE_PATH,
    UNIT_PAGE_PATH,
    UNIT_SYMBOL_PATH,
    WEAPON_PAGE_PATH,
)

ASSETS = {
    "/static/version-check.js": ("version-check.js", "text/javascript; charset=utf-8"),
    "/static/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/static/armies.js": ("armies.js", "text/javascript; charset=utf-8"),
    "/static/api.js": ("api.js", "text/javascript; charset=utf-8"),
    "/static/unit-symbols.js": ("unit-symbols.js", "text/javascript; charset=utf-8"),
    "/static/unit-presentation.js": ("unit-presentation.js", "text/javascript; charset=utf-8"),
    "/static/unit.js": ("unit.js", "text/javascript; charset=utf-8"),
    "/static/preferences.js": ("preferences.js", "text/javascript; charset=utf-8"),
    "/static/navigation.js": ("navigation.js", "text/javascript; charset=utf-8"),
    "/static/page-navigation.js": ("page-navigation.js", "text/javascript; charset=utf-8"),
    "/static/themed-logo.js": ("themed-logo.js", "text/javascript; charset=utf-8"),
    "/static/about.js": ("about.js", "text/javascript; charset=utf-8"),
    "/static/skill-extras.js": ("skill-extras.js", "text/javascript; charset=utf-8"),
    "/static/fireteams.js": ("fireteams.js", "text/javascript; charset=utf-8"),
    "/static/catalog-list.js": ("catalog-list.js", "text/javascript; charset=utf-8"),
    "/static/reference-catalog.js": (
        "reference-catalog.js",
        "text/javascript; charset=utf-8",
    ),
    "/static/reference-detail.js": (
        "reference-detail.js",
        "text/javascript; charset=utf-8",
    ),
    "/static/skill.js": ("skill.js", "text/javascript; charset=utf-8"),
    "/static/unit-list.js": ("unit-list.js", "text/javascript; charset=utf-8"),
    "/static/catalog-detail.js": ("catalog-detail.js", "text/javascript; charset=utf-8"),
    "/static/search.js": ("search.js", "text/javascript; charset=utf-8"),
    "/static/glossary.js": ("glossary.js", "text/javascript; charset=utf-8"),
    "/static/hacking-program-detail.js": (
        "hacking-program-detail.js",
        "text/javascript; charset=utf-8",
    ),
    "/static/maintained-text.js": ("maintained-text.js", "text/javascript; charset=utf-8"),
    "/static/rules-reference.js": ("rules-reference.js", "text/javascript; charset=utf-8"),
    "/static/skill-categories.js": ("skill-categories.js", "text/javascript; charset=utf-8"),
    "/static/infinitydb-logo.svg": ("infinitydb-logo.svg", "image/svg+xml"),
    "/static/fonts/Audiowide/Audiowide-Regular.woff2": (
        "fonts/Audiowide/Audiowide-Regular.woff2",
        "font/woff2",
    ),
    "/static/fonts/Oxanium/Oxanium-Variable.woff2": (
        "fonts/Oxanium/Oxanium-Variable.woff2",
        "font/woff2",
    ),
    "/static/fonts/IBM_Plex_Sans/IBMPlexSans-Variable.woff2": (
        "fonts/IBM_Plex_Sans/IBMPlexSans-Variable.woff2",
        "font/woff2",
    ),
    "/static/fonts/IBM_Plex_Sans/IBMPlexSans-Italic-Variable.woff2": (
        "fonts/IBM_Plex_Sans/IBMPlexSans-Italic-Variable.woff2",
        "font/woff2",
    ),
    "/static/fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Regular.woff2": (
        "fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Regular.woff2",
        "font/woff2",
    ),
    "/static/fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Medium.woff2": (
        "fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Medium.woff2",
        "font/woff2",
    ),
    "/static/fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-SemiBold.woff2": (
        "fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-SemiBold.woff2",
        "font/woff2",
    ),
    "/static/fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Bold.woff2": (
        "fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Bold.woff2",
        "font/woff2",
    ),
    "/static/fonts/IBM_Plex_Mono/IBMPlexMono-Regular.woff2": (
        "fonts/IBM_Plex_Mono/IBMPlexMono-Regular.woff2",
        "font/woff2",
    ),
}

_STATIC_URL = re.compile(
    r'\b(?:src|href)=(?P<quote>["\'])(?P<path>/static/[^"\']+)(?P=quote)'
)
_MODULE_IMPORT_URL = re.compile(
    r'(?P<prefix>\bfrom\s+|\bimport\s*\(\s*)(?P<quote>["\'])'
    r'(?P<path>\./[^"\']+\.js)(?P=quote)'
)
_STATIC_REVISION_FILES = tuple(sorted(filename for filename, _ in ASSETS.values()))


@dataclass(frozen=True, slots=True)
class PageSpec:
    filename: str
    breadcrumbs: tuple[tuple[str, str | None], ...]
    catalog_tag: str
    active_page: str | None = None
    template_values: tuple[tuple[str, str], ...] = ()


def _reference_page_values(
    domain_slug: str,
    *,
    intro: str,
    meta_description: str,
    detail_meta_description: str,
    summary_heading: str = "Definition",
) -> tuple[tuple[str, str], ...]:
    domain = application_domain(domain_slug)
    return (
        ("DOMAIN_SLUG", domain.slug),
        ("DOMAIN_TITLE", domain.plural_name),
        ("DOMAIN_SINGULAR", domain.singular_name),
        ("DOMAIN_SINGULAR_LOWER", domain.singular_name.lower()),
        ("DOMAIN_PLURAL_LOWER", domain.plural_name.lower()),
        ("INTRO_COPY", intro),
        ("META_DESCRIPTION", meta_description),
        ("DETAIL_META_DESCRIPTION", detail_meta_description),
        ("SUMMARY_HEADING", summary_heading),
    )


_FIXED_PAGES = {
    "/": PageSpec(
        "index.html",
        (("InfinityDB", None), ("Home", None)),
        "Player reference",
    ),
    "/armies": PageSpec(
        "armies.html",
        (("Database", "/"), ("Armies", None)),
        "Army overview",
        "armies",
    ),
    "/units": PageSpec(
        "units.html",
        (("Database", "/"), ("Units", None)),
        "Unit catalog",
        "units",
    ),
    "/search": PageSpec(
        "search.html",
        (("Database", "/"), ("Search", None)),
        "Global search",
    ),
    "/glossary": PageSpec(
        "glossary.html",
        (("Database", "/"), ("Glossary", None)),
        "Rules reference",
        "glossary",
    ),
    "/fireteams": PageSpec(
        "fireteams.html",
        (("Database", "/"), ("Fireteams", None)),
        "Fireteam charts",
        "fireteams",
    ),
    "/skill-extras": PageSpec(
        "skill-extras.html",
        (("Database", "/"), ("Skill modifiers", None)),
        "Reference data",
        "skill-extras",
    ),
    "/skills": PageSpec(
        "skills.html",
        (("Database", "/"), ("Skills", None)),
        "Rules reference",
        "skills",
    ),
    "/equipment": PageSpec(
        "equipment.html",
        (("Database", "/"), ("Equipment", None)),
        "Rules reference",
        "equipment",
    ),
    "/weapons": PageSpec(
        "weapons.html",
        (("Database", "/"), ("Weapons", None)),
        "Rules reference",
        "weapons",
    ),
    "/traits": PageSpec(
        "traits.html",
        (("Database", "/"), ("Traits", None)),
        "Rules reference",
        "traits",
    ),
    "/states": PageSpec(
        "states.html",
        (("Database", "/"), ("States", None)),
        "Rules reference",
        "states",
    ),
    "/hacking-programs": PageSpec(
        "hacking-programs.html",
        (("Database", "/"), ("Hacking Programs", None)),
        "Rules reference",
        "hacking-programs",
    ),
    "/ammunition": PageSpec(
        "reference-catalog.html",
        (("Database", "/"), ("Ammunition", None)),
        "Rules reference",
        "ammunition",
        _reference_page_values(
            "ammunition",
            intro="Browse the current N5.3 Ammunition types and their core rules effects.",
            meta_description="Browse Infinity N5.3 Ammunition types and concise rules references.",
            detail_meta_description="View Infinity N5.3 Ammunition rules details.",
            summary_heading="Rules reference",
        ),
    ),
    "/labels": PageSpec(
        "reference-catalog.html",
        (("Database", "/"), ("Labels", None)),
        "Rules reference",
        "labels",
        _reference_page_values(
            "labels",
            intro=(
                "Browse the canonical Labels used to classify Skills, Equipment, and "
                "rules effects."
            ),
            meta_description="Browse Infinity rules Labels and their canonical definitions.",
            detail_meta_description="View the canonical definition of an Infinity rules Label.",
        ),
    ),
    "/about": PageSpec(
        "about.html",
        (("InfinityDB", "/"), ("About", None)),
        "Player reference",
        "about",
    ),
}
_DETAIL_PAGES = (
    (
        UNIT_PAGE_PATH,
        PageSpec(
            "unit.html",
            (("Database", "/"), ("Units", "/units"), ("Details", None)),
            "Unit catalog",
            "units",
        ),
    ),
    (
        SKILL_PAGE_PATH,
        PageSpec(
            "skill.html",
            (("Database", "/"), ("Skills", "/skills"), ("Details", None)),
            "Rules reference",
            "skills",
        ),
    ),
    (
        EQUIPMENT_PAGE_PATH,
        PageSpec(
            "equipment-detail.html",
            (("Database", "/"), ("Equipment", "/equipment"), ("Details", None)),
            "Rules reference",
            "equipment",
        ),
    ),
    (
        WEAPON_PAGE_PATH,
        PageSpec(
            "weapons-detail.html",
            (("Database", "/"), ("Weapons", "/weapons"), ("Details", None)),
            "Rules reference",
            "weapons",
        ),
    ),
    (
        TRAIT_PAGE_PATH,
        PageSpec(
            "traits-detail.html",
            (("Database", "/"), ("Traits", "/traits"), ("Details", None)),
            "Rules reference",
            "traits",
        ),
    ),
    (
        STATE_PAGE_PATH,
        PageSpec(
            "states-detail.html",
            (("Database", "/"), ("States", "/states"), ("Details", None)),
            "Rules reference",
            "states",
        ),
    ),
    (
        AMMUNITION_PAGE_PATH,
        PageSpec(
            "reference-detail.html",
            (("Database", "/"), ("Ammunition", "/ammunition"), ("Details", None)),
            "Rules reference",
            "ammunition",
            _reference_page_values(
                "ammunition",
                intro="Browse the current N5.3 Ammunition types and their core rules effects.",
                meta_description=(
                    "Browse Infinity N5.3 Ammunition types and concise rules references."
                ),
                detail_meta_description="View Infinity N5.3 Ammunition rules details.",
                summary_heading="Rules reference",
            ),
        ),
    ),
    (
        LABEL_PAGE_PATH,
        PageSpec(
            "reference-detail.html",
            (("Database", "/"), ("Labels", "/labels"), ("Details", None)),
            "Rules reference",
            "labels",
            _reference_page_values(
                "labels",
                intro=(
                    "Browse the canonical Labels used to classify Skills, Equipment, and "
                    "rules effects."
                ),
                meta_description="Browse Infinity rules Labels and their canonical definitions.",
                detail_meta_description=(
                    "View the canonical definition of an Infinity rules Label."
                ),
            ),
        ),
    ),
    (
        HACKING_PROGRAM_PAGE_PATH,
        PageSpec(
            "hacking-program-detail.html",
            (
                ("Database", "/"),
                ("Hacking Programs", "/hacking-programs"),
                ("Details", None),
            ),
            "Rules reference",
            "hacking-programs",
        ),
    ),
)


def _static_asset_revision() -> str:
    """Fingerprint cache-immutable browser assets and the canonical symbol contract."""

    static = files("infinity_db.web").joinpath("static")
    digest = sha256()
    for filename in _STATIC_REVISION_FILES:
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256(static.joinpath(*filename.split("/")).read_bytes()).digest())

    publication_manifest = maintained_manifest_path("symbol-publication.json")
    digest.update(b"data/manifests/symbol-publication.json\0")
    digest.update(sha256(publication_manifest.read_bytes()).digest())
    return digest.hexdigest()[:16]


STATIC_ASSET_REVISION = _static_asset_revision()
STATIC_ASSET_VERSION = f"{__version__}-{STATIC_ASSET_REVISION}"


def _version_static_urls(document: str) -> str:
    """Give page assets a content-derived immutable URL."""

    return _STATIC_URL.sub(
        lambda match: (
            f"{match.group(0)[:-1]}?v={STATIC_ASSET_VERSION}{match.group('quote')}"
        ),
        document,
    )


def _asset_cache_control(query: str) -> str:
    """Cache fingerprinted assets forever and imported modules briefly."""

    version = parse_qs(query).get("v")
    if version == [STATIC_ASSET_VERSION]:
        return "public, max-age=31536000, immutable"
    return "public, max-age=300, stale-while-revalidate=600"


def _version_module_imports(source: str) -> str:
    """Keep an ES module and every relative dependency in the same release."""

    return _MODULE_IMPORT_URL.sub(
        lambda match: (
            f"{match.group('prefix')}{match.group('quote')}"
            f"{match.group('path')}?v={STATIC_ASSET_VERSION}{match.group('quote')}"
        ),
        source,
    )


def _render_page(
    spec: PageSpec,
    *,
    source_data_changed_on: date | None,
    snapshot_downloaded_on: date | None,
    snapshot_revision: str,
) -> bytes:
    """Render a page with the project-wide navigation and page shell."""

    static = files("infinity_db.web").joinpath("static")
    navigation = static.joinpath("navigation.html").read_text(encoding="utf-8")
    navigation_markers = {
        "armies": "ARMIES_CURRENT",
        "units": "UNIT_EXPLORER_CURRENT",
        "skills": "SKILLS_CURRENT",
        "equipment": "EQUIPMENT_CURRENT",
        "weapons": "WEAPONS_CURRENT",
        "traits": "TRAITS_CURRENT",
        "states": "STATES_CURRENT",
        "hacking-programs": "HACKING_PROGRAMS_CURRENT",
        "ammunition": "AMMUNITION_CURRENT",
        "labels": "LABELS_CURRENT",
        "skill-extras": "SKILL_EXTRAS_CURRENT",
        "fireteams": "FIRETEAMS_CURRENT",
        "glossary": "GLOSSARY_CURRENT",
        "about": "ABOUT_CURRENT",
    }
    for page, marker_name in navigation_markers.items():
        navigation = navigation.replace(
            f"{{{{{marker_name}}}}}",
            ' aria-current="page"' if spec.active_page == page else "",
        )
    navigation = navigation.replace(
        "{{ARMY_DATA_DATES}}",
        (
            (
                '<p class="snapshot-date">Army data last changed '
                f'<time datetime="{source_data_changed_on.isoformat()}">'
                f"{source_data_changed_on:%B} {source_data_changed_on.day}, "
                f"{source_data_changed_on:%Y}"
                "</time></p>"
            )
            if source_data_changed_on
            else ""
        )
        + (
            '<p class="snapshot-date developer-only">Snapshot downloaded '
            f'<time datetime="{snapshot_downloaded_on.isoformat()}">'
            f"{snapshot_downloaded_on:%B} {snapshot_downloaded_on.day}, "
            f"{snapshot_downloaded_on:%Y}"
            "</time></p>"
            if snapshot_downloaded_on
            else ""
        ),
    )
    breadcrumb_markup = "".join(
        (
            f'<a href="{escape(href, quote=True)}">{escape(label)}</a>'
            if href
            else f"<strong>{escape(label)}</strong>"
        )
        + ('<span aria-hidden="true">/</span>' if index < len(spec.breadcrumbs) - 1 else "")
        for index, (label, href) in enumerate(spec.breadcrumbs)
    )
    page_header = (
        static.joinpath("page-header.html")
        .read_text(encoding="utf-8")
        .replace("{{BREADCRUMBS}}", breadcrumb_markup)
        .replace("{{CATALOG_TAG}}", escape(spec.catalog_tag))
    )
    page_footer = (
        static.joinpath("page-footer.html")
        .read_text(encoding="utf-8")
        .replace("{{VERSION}}", escape(__display_version__))
    )
    document = static.joinpath(spec.filename).read_text(encoding="utf-8")
    for key, value in spec.template_values:
        document = document.replace(f"{{{{{key}}}}}", escape(value, quote=True))
    return _version_static_urls(
        document.replace(
            '<html lang="en">',
            f'<html lang="en" data-app-version="{__version__}" '
            f'data-static-version="{STATIC_ASSET_VERSION}" '
            f'data-static-revision="{STATIC_ASSET_REVISION}" '
            f'data-snapshot-revision="{snapshot_revision}">',
        )
        .replace(
            "</head>",
            (
                '<script type="module" '
                f'src="/static/version-check.js?v={STATIC_ASSET_VERSION}"></script>'
                "</head>"
            ),
        )
        .replace("<!-- navigation -->", navigation)
        .replace("<!-- page-header -->", page_header)
        .replace("<!-- page-footer -->", page_footer)
    ).encode("utf-8")


class PresentationHandler:
    """Serve browser documents, their shared shell, and packaged static assets."""

    def __init__(
        self,
        *,
        source_data_changed_on: date | None,
        snapshot_downloaded_on: date | None,
        snapshot_revision: str,
    ) -> None:
        self.source_data_changed_on = source_data_changed_on
        self.snapshot_downloaded_on = snapshot_downloaded_on
        self.snapshot_revision = snapshot_revision

    def _page_response(self, spec: PageSpec) -> WebResponse:
        return WebResponse(
            body=_render_page(
                spec,
                source_data_changed_on=self.source_data_changed_on,
                snapshot_downloaded_on=self.snapshot_downloaded_on,
                snapshot_revision=self.snapshot_revision,
            ),
            content_type="text/html; charset=utf-8",
        )

    def handle(self, path: str, query: str) -> WebResponse | None:
        """Return a presentation response, or None when this handler does not own the path."""

        if spec := _FIXED_PAGES.get(path):
            return self._page_response(spec)

        if path in ASSETS:
            filename, content_type = ASSETS[path]
            body = files("infinity_db.web").joinpath(
                "static", *filename.split("/")
            ).read_bytes()
            version = parse_qs(query).get("v")
            if filename.endswith(".js") and version == [STATIC_ASSET_VERSION]:
                body = _version_module_imports(body.decode("utf-8")).encode("utf-8")
            return WebResponse(
                body=body,
                content_type=content_type,
                cache_control=_asset_cache_control(query),
            )

        symbol = self._symbol_response(path, query)
        if symbol is not None:
            return symbol

        for pattern, spec in _DETAIL_PAGES:
            if pattern.fullmatch(path):
                return self._page_response(spec)
        return None

    @staticmethod
    def _symbol_response(path: str, query: str) -> WebResponse | None:
        asset = None
        if ARMY_SYMBOL_PATH.fullmatch(path):
            filename = path.removeprefix("/static/armies/")
            asset = files("infinity_db.web").joinpath("static", "armies", filename)
        elif UNIT_SYMBOL_PATH.fullmatch(path):
            filename = path.removeprefix("/static/units/")
            asset = files("infinity_db.web").joinpath("static", "units", filename)
        elif match := ORDER_SYMBOL_PATH.fullmatch(path):
            asset = files("infinity_db.web").joinpath(
                "static", "orders", f"{match.group(1)}.svg"
            )
        elif match := CHARACTERISTIC_SYMBOL_PATH.fullmatch(path):
            asset = files("infinity_db.web").joinpath(
                "static", "characteristics", f"{match.group(1)}.svg"
            )
        else:
            return None

        if not asset.is_file():
            return WebResponse.json({"error": "Resource not found"}, status=HTTPStatus.NOT_FOUND)
        return WebResponse(
            body=asset.read_bytes(),
            content_type="image/svg+xml",
            cache_control=_asset_cache_control(query),
        )
