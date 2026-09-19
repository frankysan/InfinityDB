"""Concise interactive console output with a complete verbose pipeline log."""

from __future__ import annotations

import re
import sys
import traceback as traceback_module
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TextIO

_PROGRESS_RE = re.compile(r"\[(\d+)/(\d+)\]")


class _CapturedStream:
    """Write verbatim to the log and expose progress-looking lines to the console."""

    def __init__(self, owner: PipelineConsole) -> None:
        self.owner = owner
        self._buffer = ""

    @property
    def encoding(self) -> str:
        return "utf-8"

    def write(self, text: str) -> int:
        if not text:
            return 0
        self.owner._write_log(text)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self.owner._observe_verbose_line(line.rstrip("\r"))
        return len(text)

    def flush(self) -> None:
        self.owner._flush_log()

    def isatty(self) -> bool:
        return False


class PipelineConsole:
    """Keep verbose tool output in a log while presenting compact stage progress."""

    def __init__(
        self,
        *,
        log_path: Path,
        stage_labels: dict[str, str],
        stage_order: tuple[str, ...],
        started_at: datetime | None = None,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
    ) -> None:
        self.log_path = log_path
        self.stage_labels = stage_labels
        self.stage_order = stage_order
        self.started_at = started_at or datetime.now().astimezone()
        self._console_out = stdout or sys.stdout
        self._console_err = stderr or sys.stderr
        self._interactive = bool(getattr(self._console_out, "isatty", lambda: False)())
        self._log: TextIO | None = None
        self._stdout_capture = _CapturedStream(self)
        self._stderr_capture = _CapturedStream(self)
        self._old_stdout: TextIO | None = None
        self._old_stderr: TextIO | None = None
        self._active_stage: str | None = None
        self._active_detail = ""
        self._rendered_width = 0

    @staticmethod
    def default_log_path(data_root: Path, *, now: datetime | None = None) -> Path:
        """Return a collision-safe timestamped default log path."""
        timestamp = now or datetime.now().astimezone()
        directory = data_root / "logs" / "symbols"
        stem = f"SYMBOL BUILD {timestamp.strftime('%Y%m%d-%H%M%S')}"
        candidate = directory / f"{stem}.log"
        suffix = 2
        while candidate.exists():
            candidate = directory / f"{stem}-{suffix}.log"
            suffix += 1
        return candidate

    def __enter__(self) -> PipelineConsole:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = self.log_path.open("x", encoding="utf-8", newline="\n", buffering=1)
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr
        sys.stdout = self._stdout_capture  # type: ignore[assignment]
        sys.stderr = self._stderr_capture  # type: ignore[assignment]
        self._write_log(
            "InfinityDB symbol pipeline log\n"
            f"Started: {self.started_at.isoformat(timespec='seconds')}\n"
            f"Log: {self.log_path}\n\n"
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None and exc is not None and self._log is not None:
            self._write_log("\nUNHANDLED EXCEPTION\n")
            traceback_module.print_exception(exc_type, exc, traceback, file=self._log)
        if self._stdout_capture._buffer:
            self._observe_verbose_line(self._stdout_capture._buffer.rstrip("\r"))
        if self._stderr_capture._buffer:
            self._observe_verbose_line(self._stderr_capture._buffer.rstrip("\r"))
        if self._old_stdout is not None:
            sys.stdout = self._old_stdout
        if self._old_stderr is not None:
            sys.stderr = self._old_stderr
        self._clear_progress_line()
        if self._log is not None:
            self._log.close()
            self._log = None

    def header(self, *, mode: str) -> None:
        self.line("InfinityDB symbol pipeline")
        self.line(f"Mode: {mode}")
        self.line(f"Log: {self.log_path}")
        self.line("")

    def line(self, text: str, *, error: bool = False) -> None:
        """Emit one persistent console line and copy it to the verbose log."""
        self._clear_progress_line()
        stream = self._console_err if error else self._console_out
        stream.write(text + "\n")
        stream.flush()
        self._write_log(text + "\n")
        if self._active_stage is not None and self._interactive:
            self._render_stage()

    def stage_start(self, stage: str, *, detail: str = "") -> None:
        self._active_stage = stage
        self._active_detail = detail
        self._write_log(f"\n[{stage}] START" + (f" | {detail}" if detail else "") + "\n")
        if self._interactive:
            self._render_stage()
        else:
            self._console_out.write(self._stage_text(status="RUNNING") + "\n")
            self._console_out.flush()

    def stage_progress(self, current: int, total: int, *, detail: str = "") -> None:
        if self._active_stage is None or total < 1:
            return
        progress = f"{current}/{total}"
        self._active_detail = f"{progress} {detail}".strip()
        if self._interactive:
            self._render_stage()

    def stage_success(self, detail: str = "", *, existing: bool = False) -> None:
        if self._active_stage is None:
            return
        status = "PASS (existing)" if existing else "PASS"
        stage = self._active_stage
        text = self._stage_text(status=status, detail=detail)
        self._finish_stage_line(text)
        self._write_log(f"[{stage}] {status}" + (f" | {detail}" if detail else "") + "\n")
        self._active_stage = None
        self._active_detail = ""

    def stage_failed(self, detail: str) -> None:
        if self._active_stage is None:
            self.line(f"ERROR: {detail}", error=True)
            return
        stage = self._active_stage
        text = self._stage_text(status="FAIL", detail=detail)
        self._finish_stage_line(text, error=True)
        self._write_log(f"[{stage}] FAIL | {detail}\n")
        self._active_stage = None
        self._active_detail = ""

    def checkpoint(self, stage: str) -> None:
        self.line(f"Checkpoint: {stage}")

    def _stage_text(
        self,
        *,
        status: str,
        detail: str | None = None,
    ) -> str:
        assert self._active_stage is not None
        index = self.stage_order.index(self._active_stage) + 1
        label = self.stage_labels.get(self._active_stage, self._active_stage)
        suffix = self._active_detail if detail is None else detail
        base = f"[{index}/{len(self.stage_order)}] {label:<22} {status}"
        return f"{base}  {suffix}" if suffix else base

    def _render_stage(self) -> None:
        if not self._interactive or self._active_stage is None:
            return
        text = self._stage_text(status="RUNNING")
        padding = " " * max(0, self._rendered_width - len(text))
        self._console_out.write("\r" + text + padding)
        self._console_out.flush()
        self._rendered_width = len(text)

    def _finish_stage_line(self, text: str, *, error: bool = False) -> None:
        stream = self._console_err if error else self._console_out
        if self._interactive:
            padding = " " * max(0, self._rendered_width - len(text))
            stream.write("\r" + text + padding + "\n")
            self._rendered_width = 0
        else:
            stream.write(text + "\n")
        stream.flush()

    def _clear_progress_line(self) -> None:
        if not self._interactive or self._rendered_width == 0:
            return
        self._console_out.write("\r" + (" " * self._rendered_width) + "\r")
        self._console_out.flush()
        self._rendered_width = 0

    def _observe_verbose_line(self, line: str) -> None:
        if self._active_stage is None:
            return
        match = _PROGRESS_RE.search(line)
        if match is None:
            return
        self.stage_progress(int(match.group(1)), int(match.group(2)))

    def _write_log(self, text: str) -> None:
        if self._log is not None:
            self._log.write(text)

    def _flush_log(self) -> None:
        if self._log is not None:
            self._log.flush()
