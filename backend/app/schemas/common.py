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


def ts_cursor(row_ts, row_id) -> str:
    """Cursor for a (timestamp, id) keyset; pair with `parse_ts_cursor`."""
    return encode_cursor({"k": [row_ts.isoformat(), str(row_id)]})


def parse_ts_cursor(cursor: str):
    import uuid
    from datetime import datetime

    try:
        raw = decode_cursor(cursor)["k"]
        return datetime.fromisoformat(raw[0]), uuid.UUID(raw[1])
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise AppError("Invalid cursor", code="invalid_cursor") from exc
