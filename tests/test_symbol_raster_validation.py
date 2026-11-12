from pathlib import Path

import pytest

from tools import symbol_raster_validation as raster

Image = pytest.importorskip("PIL.Image")


def test_raster_comparison_detects_difference_visible_on_white(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = tmp_path / "reference.svg"
    matching = tmp_path / "matching.svg"
    changed = tmp_path / "changed.svg"
    reference.write_text("transparent", encoding="utf-8")
    matching.write_text("transparent", encoding="utf-8")
    changed.write_text("opaque", encoding="utf-8")

    def render(_renderer: str, _executable: str, source: Path, output: Path, _width: int):
        output.parent.mkdir(parents=True, exist_ok=True)
        alpha = 0 if source.read_text(encoding="utf-8") == "transparent" else 255
        Image.new("RGBA", (2, 2), (0, 0, 0, alpha)).save(output)
        return True, ""

    monkeypatch.setattr(raster, "render_png", render)
    validator = raster.RasterValidator(
        renderer="resvg", executable="resvg", reference_svg=reference,
        temp_root=tmp_path / "renders", target_sizes=[32], dprs=[1.0, 2.0],
        max_rms=0.01, max_changed_fraction=0.01, pixel_diff_threshold=8,
    )
    assert validator.prepare_reference() == (True, "")
    assert validator.validate(matching, "matching")[0]
    passed, metrics, error = validator.validate(changed, "changed")
    assert not passed
    assert error == ""
    assert metrics.worst_rms == 1.0
    assert metrics.worst_changed_fraction == 1.0
    assert metrics.worst_background == "white"


def test_missing_pillow_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(raster, "Image", None)
    with pytest.raises(RuntimeError, match="Missing dependency: Pillow"):
        raster.compare_pngs(Path("reference.png"), Path("candidate.png"), 8)
