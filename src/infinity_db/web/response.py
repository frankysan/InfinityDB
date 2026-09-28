"""Small internal HTTP response value shared by web-layer route handlers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any


@dataclass(slots=True)
class WebResponse:
    """One handler response before WSGI-level headers and instrumentation are applied."""

    status: HTTPStatus = HTTPStatus.OK
    body: bytes = b""
    content_type: str = "application/json; charset=utf-8"
    cache_control: str = "no-cache"
    headers: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def json(
        cls,
        payload: Any,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        cache_control: str = "no-cache",
        headers: list[tuple[str, str]] | None = None,
    ) -> WebResponse:
        return cls(
            status=status,
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            cache_control=cache_control,
            headers=list(headers or ()),
        )
