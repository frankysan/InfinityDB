from pathlib import Path
from types import SimpleNamespace

import tools.svg_processor as svg_processor


def test_duplicate_detection_exact_first_visual_and_canonical_ranking(
    tmp_path: Path, monkeypatch
) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    exact = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'
    (input_root / "a.svg").write_text(exact, encoding="utf-8")
    (input_root / "b.svg").write_text(exact, encoding="utf-8")
    (input_root / "c.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0,0"/></svg>',
        encoding="utf-8",
    )
    (input_root / "d.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><path d="M1 1"/></svg>',
        encoding="utf-8",
    )

    monkeypatch.setattr(svg_processor, "pillow_image_module", lambda: object())
    monkeypatch.setattr(
        svg_processor, "resolve_duplicate_renderer", lambda _requested: ("resvg", "resvg")
    )
    monkeypatch.setattr(svg_processor, "executable_version", lambda _path: "test")

    def fake_render(_renderer, _executable, _source, destination, _size):
        destination.write_bytes(b"png")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(svg_processor, "render_svg_for_duplicate_check", fake_render)

    def fake_pixel_hash(path: Path) -> str:
        index = int(path.stem.rsplit("-", 1)[1])
        return "same" if index in {1, 2} else "different"

    monkeypatch.setattr(svg_processor, "rgba_pixel_hash", fake_pixel_hash)

    result = svg_processor.find_duplicate_svgs(
        input_root,
        output_root,
        {
            "a.svg": "fonts_available",
            "b.svg": "fonts_available",
            "c.svg": "no_active_text",
            "d.svg": "no_active_text",
        },
        jobs=1,
    )

    assert result["source_svg_files"] == 4
    assert result["unique_byte_sets"] == 3
    assert result["renders_avoided_exact"] == 1
    assert result["exact_groups"] == 0
    assert result["visual_groups"] == 1
    assert result["redundant_files"] == 2
    assert result["duplicate_representatives"] == {
        "a.svg": "c.svg",
        "b.svg": "c.svg",
    }
    report = result["report_path"].read_text(encoding="utf-8-sig")
    assert "representative,c.svg,no_active_text,c.svg" in report
