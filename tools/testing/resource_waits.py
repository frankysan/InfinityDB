"""Per-test resource waiting measurements, independent of pytest phase timings.

Only waits occurring inside an explicitly captured setup phase are attributed
to an individual test. The capture is context-local and safe for nested calls.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_ACTIVE_WAITS: ContextVar[list[tuple[str, float]] | None] = ContextVar(
    "infinitydb_resource_waits", default=None,
)


@contextmanager
def capture_resource_waits() -> Iterator[list[tuple[str, float]]]:
    """Collect measured resource waits for the currently executing setup."""
    waits: list[tuple[str, float]] = []
    token = _ACTIVE_WAITS.set(waits)
    try:
        yield waits
    finally:
        _ACTIVE_WAITS.reset(token)


def record_resource_wait(resource: str, seconds: float) -> None:
    """Attribute an acquired/failed wait to the active test setup, if any."""
    waits = _ACTIVE_WAITS.get()
    if waits is not None and seconds >= 0:
        waits.append((resource, seconds))
