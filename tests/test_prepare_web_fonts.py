from __future__ import annotations

from pathlib import Path

from tools.prepare_web_fonts import FACES, LICENSES, README

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FONT_ROOT = PROJECT_ROOT / "src" / "infinity_db" / "web" / "static" / "fonts"


def test_published_web_fonts_match_the_preparation_contract() -> None:
    expected = {Path(spec.destination).as_posix() for spec in FACES}
    expected.update(Path(target).as_posix() for _, target in LICENSES)
    expected.add("README.md")

    published = {
        path.relative_to(FONT_ROOT).as_posix()
        for path in FONT_ROOT.rglob("*.woff2")
        if path.is_file()
    }
    assert published == {Path(spec.destination).as_posix() for spec in FACES}
    for _, target in LICENSES:
        assert (FONT_ROOT / target).is_file()
    assert (FONT_ROOT / "README.md").is_file()

    for spec in FACES:
        payload = (FONT_ROOT / spec.destination).read_bytes()
        assert payload.startswith(b"wOF2")

    assert (FONT_ROOT / "README.md").read_text(encoding="utf-8") == README
    for _, target in LICENSES:
        license_text = (FONT_ROOT / target).read_text(encoding="utf-8")
        assert "SIL Open Font License" in license_text
        assert "Version 1.1" in license_text
