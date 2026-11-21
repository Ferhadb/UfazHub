import uuid
from typing import Literal

from pydantic import BaseModel

from app.core.signing import sign_media
from app.models.media import Attachment


class AttachmentOut(BaseModel):
    id: uuid.UUID
    kind: Literal["image", "file"]
    mime: str
    size: int
    name: str
    width: int | None = None
    height: int | None = None
    urls: dict[str, str]  # variant -> signed, expiring URL (`sm`/`md`/`lg`, or `file`)

    @classmethod
    def of(cls, a: Attachment) -> "AttachmentOut":
        names = list(a.variants) or ["file"]
        return cls(
            id=a.id,
            kind=a.kind,  # type: ignore[arg-type]
            mime=a.mime,
            size=a.size,
            name=a.original_name,
            width=a.width,
            height=a.height,
            urls={n: sign_media(a.id, n) for n in names},
        )
