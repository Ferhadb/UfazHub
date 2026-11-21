"""Uploads: size limits, content-sniffed MIME, Pillow image variants, virus-scan hook, storage."""

import asyncio
import io
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.storage import get_storage
from app.models.media import Attachment
from app.models.user import User

Purpose = Literal["avatar", "cover", "attachment"]

Image.MAX_IMAGE_PIXELS = (
    40_000_000  # Pillow refuses images far above this (decompression bombs)
)

# (signature check, mime). We trust bytes, never the client's Content-Type or file name.
IMAGE_MIMES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
PDF = "application/pdf"
# variant name -> bounding box (longest side); avatars are square crops instead.
SIZES = {"sm": 320, "md": 800, "lg": 1600}
AVATAR_SIZES = {"sm": 64, "md": 256}


def sniff(head: bytes) -> str | None:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"%PDF-"):
        return PDF
    return None


Scanner = Callable[[bytes, str], Awaitable[None]]


async def _no_scan(data: bytes, mime: str) -> None:
    """Default scanner: accepts everything. Swap in ClamAV etc. via `set_scanner`."""


_scanner: Scanner = _no_scan


def set_scanner(scanner: Scanner) -> None:
    """Virus-scan hook point. A scanner raises AppError (e.g. 422 `infected`) to reject."""
    global _scanner
    _scanner = scanner


def _encode(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=82, method=4)  # no exif is copied: metadata is dropped
    return buf.getvalue()


def make_variants(data: bytes, purpose: Purpose) -> tuple[tuple[int, int], dict]:
    """Return ((w, h) of the original, {variant: (webp bytes, w, h)}). Blocking: run in a thread."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            im = ImageOps.exif_transpose(im)
            size = im.size
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise AppError(
            "That image could not be read.", code="invalid_image", status_code=422
        ) from exc
    out = {}
    if purpose == "avatar":
        for name, px in AVATAR_SIZES.items():
            sq = ImageOps.fit(im, (px, px), Image.Resampling.LANCZOS)
            out[name] = (_encode(sq), px, px)
    else:
        for name, px in SIZES.items():
            copy = im.copy()
            copy.thumbnail((px, px), Image.Resampling.LANCZOS)  # never upscales
            out[name] = (_encode(copy), *copy.size)
    return size, out


async def _read_capped(upload: UploadFile, limit_for: Callable[[bytes], int]) -> bytes:
    data = b""
    limit = None
    while chunk := await upload.read(64 * 1024):
        data += chunk
        if limit is None:
            limit = limit_for(data)
        if len(data) > limit:
            raise AppError(
                f"File is too large (max {limit // (1024 * 1024)} MB).",
                code="payload_too_large",
                status_code=413,
            )
    return data


def _safe_name(name: str | None) -> str:
    return (
        re.sub(r"[^\w.\- ]+", "_", (name or "upload").rsplit("/", 1)[-1])[:200]
        or "upload"
    )


async def store_upload(
    db: AsyncSession, user: User, upload: UploadFile, purpose: Purpose
) -> Attachment:
    def limit_for(head: bytes) -> int:
        return (
            settings.IMAGE_MAX_BYTES
            if sniff(head) in IMAGE_MIMES
            else settings.UPLOAD_MAX_BYTES
        )

    data = await _read_capped(upload, limit_for)
    mime = sniff(data[:16])
    allowed = IMAGE_MIMES if purpose != "attachment" else IMAGE_MIMES | {PDF}
    if mime not in allowed:
        raise AppError(
            "Unsupported file type. Use PNG, JPEG, GIF or WebP"
            + (
                " (PDF also works for attachments)." if purpose == "attachment" else "."
            ),
            code="unsupported_media_type",
            status_code=415,
        )
    if len(data) > (
        settings.IMAGE_MAX_BYTES if mime in IMAGE_MIMES else settings.UPLOAD_MAX_BYTES
    ):
        raise AppError("File is too large.", code="payload_too_large", status_code=413)
    await _scanner(data, mime)

    storage = get_storage()
    att = Attachment(
        id=uuid.uuid4(),
        owner_id=user.id,
        kind="image" if mime in IMAGE_MIMES else "file",
        mime=mime,
        size=len(data),
        original_name=_safe_name(upload.filename),
    )
    if att.kind == "image":
        (att.width, att.height), variants = await asyncio.to_thread(
            make_variants, data, purpose
        )
        att.variants = {}
        for name, (blob, w, h) in variants.items():
            key = f"{att.id}/{name}.webp"
            await storage.put(key, blob)
            att.variants[name] = {
                "key": key,
                "mime": "image/webp",
                "width": w,
                "height": h,
            }
        att.mime = "image/webp"
    else:
        key = f"{att.id}/file.pdf"
        await storage.put(key, data)
        att.variants = {"file": {"key": key, "mime": mime}}
    att.variants = dict(att.variants)
    db.add(att)
    await db.flush()
    if purpose == "avatar":
        old, user.avatar_attachment_id = user.avatar_attachment_id, att.id
        await db.flush()
        if old:
            await delete_attachment(db, old)
    return att


async def delete_attachment(db: AsyncSession, attachment_id: uuid.UUID) -> None:
    att = await db.get(Attachment, attachment_id)
    if att is None:
        return
    storage = get_storage()
    for v in att.variants.values():
        await storage.delete(v["key"])
    await db.delete(att)
    await db.flush()


async def owned_attachment(
    db: AsyncSession, user: User, attachment_id: uuid.UUID, kind: str | None
) -> Attachment:
    """Attach only files you uploaded yourself (admins may reuse any)."""
    att = await db.get(Attachment, attachment_id)
    if att is None or (att.owner_id != user.id and user.role != "admin"):
        raise AppError(
            "Unknown attachment.",
            code="invalid_attachment",
            status_code=422,
            fields={"attachment": "Upload the file first."},
        )
    if kind and att.kind != kind:
        raise AppError(
            f"Expected {kind}.",
            code="invalid_attachment",
            status_code=422,
            fields={"attachment": f"Must be an {kind}."},
        )
    return att
