import io
from datetime import UTC, datetime
from pathlib import Path

from tools.pipeline_console import PipelineConsole


class TtyBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_pipeline_console_keeps_verbose_output_in_log_and_updates_one_line(
    tmp_path: Path,
) -> None:
    output = TtyBuffer()
    errors = TtyBuffer()
    log = tmp_path / "symbols.log"
    console = PipelineConsole(
        log_path=log,
        stage_labels={"snapshot": "Snapshot", "acquisition": "Symbol acquisition"},
        stage_order=("snapshot", "acquisition"),
        started_at=datetime(2026, 9, 19, 10, 30, tzinfo=UTC),
        stdout=output,
        stderr=errors,
    )

    with console:
        console.stage_start("acquisition", detail="resolving symbols")
        print("verbose discovery detail")
        print("[1/3] units/a.svg [cache]")
        print("[2/3] units/b.svg [cache]")
        print("[3/3] units/c.svg [network]")
        console.stage_success("3 assets")

    console_text = output.getvalue()
    assert "verbose discovery detail" not in console_text
    assert "units/a.svg" not in console_text
    assert "1/3" in console_text
    assert "3/3" in console_text
    assert "PASS  3 assets" in console_text
    assert "\r" in console_text
    assert errors.getvalue() == ""

    log_text = log.read_text(encoding="utf-8")
    assert "verbose discovery detail" in log_text
    assert "[1/3] units/a.svg [cache]" in log_text
    assert "[3/3] units/c.svg [network]" in log_text
    assert "[acquisition] PASS | 3 assets" in log_text


def test_default_symbol_log_path_is_timestamped_and_collision_safe(tmp_path: Path) -> None:
    now = datetime(2026, 9, 19, 10, 24, 31, tzinfo=UTC)
    first = PipelineConsole.default_log_path(tmp_path, now=now)
    first.parent.mkdir(parents=True)
    first.write_text("first", encoding="utf-8")

    second = PipelineConsole.default_log_path(tmp_path, now=now)

    assert first == tmp_path / "logs" / "symbols" / "SYMBOL BUILD 20260919-102431.log"
    assert second == tmp_path / "logs" / "symbols" / "SYMBOL BUILD 20260919-102431-2.log"
