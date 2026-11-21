import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile

from app.api.deps import DB
from app.api.permissions import VerifiedUser
from app.core.config import settings
from app.core.errors import AppError, NotFound
from app.core.ratelimit import limit_upload
from app.core.signing import verify_media
from app.core.storage import get_storage
from app.models.media import Attachment
from app.schemas.media import AttachmentOut
from app.services import uploads as svc

router = APIRouter(tags=["uploads"])


@router.post(
    "/uploads",
    status_code=201,
    response_model=AttachmentOut,
    dependencies=[Depends(limit_upload)],
)
async def upload(
    request: Request,
    db: DB,
    user: VerifiedUser,
    file: Annotated[UploadFile, File()],
    purpose: Annotated[svc.Purpose, Form()] = "attachment",
):
    # Cheap early refusal; the streamed read enforces the real cap.
    declared = int(request.headers.get("content-length") or 0)
    if declared > settings.UPLOAD_MAX_BYTES + 1024 * 1024:
        raise AppError("File is too large.", code="payload_too_large", status_code=413)
    att = await svc.store_upload(db, user, file, purpose)
    await db.commit()
    return AttachmentOut.of(att)


@router.get("/media/{attachment_id}/{variant}", include_in_schema=False)
async def media(
    attachment_id: uuid.UUID,
    variant: str,
    db: DB,
    exp: Annotated[int, Query()],
    sig: Annotated[str, Query(max_length=64)],
):
    """Serve a file for a valid signed URL; expired or tampered URLs look like missing files."""
    if not verify_media(attachment_id, variant, exp, sig):
        raise NotFound("Not found.")
    att = await db.get(Attachment, attachment_id)
    v = att.variants.get(variant) if att else None
    if att is None or v is None:
        raise NotFound("Not found.")
    data = await get_storage().get(v["key"])
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=600",
    }
    if att.kind == "file":  # never rendered inline from our origin
        headers["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{quote(att.original_name)}"
        )
    return Response(data, media_type=v["mime"], headers=headers)
