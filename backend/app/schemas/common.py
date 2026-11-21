"""Shared response shapes."""

import base64
import json
from typing import Any

from pydantic import BaseModel

from app.core.errors import AppError


class Page[T](BaseModel):
    """Cursor page: `next_cursor` is null on the last page. No unbounded lists anywhere."""

    items: list[T]
    next_cursor: str | None = None


def encode_cursor(payload: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except ValueError as exc:  # also covers binascii and UnicodeDecodeError
        raise AppError("Invalid cursor", code="invalid_cursor") from exc
    if not isinstance(data, dict):
        raise AppError("Invalid cursor", code="invalid_cursor")
    return data
