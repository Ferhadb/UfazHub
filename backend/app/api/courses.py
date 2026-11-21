import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB
from app.api.permissions import (
    ActiveUser,
    AdminUser,
    OptionalUser,
    can_manage,
    not_found_unless_visible,
)
from app.core.errors import Forbidden, NotFound
from app.core.ratelimit import limit_write
from app.models.content import ContentItem
from app.schemas.common import Page
from app.schemas.library import (
    AttachIn,
    CourseDetail,
    CourseIn,
    CourseOut,
    ItemCard,
    PathIn,
    ProgramIn,
    ProgramOut,
    ProgramRef,
)
from app.services import courses as svc

router = APIRouter(tags=["courses"])


@router.get("/programs", response_model=list[ProgramOut])
async def programs(db: DB):
    """Every program with its courses; admin-curated and capped, so not paged."""
    return await svc.list_programs(db)


@router.get("/courses/{slug}", response_model=CourseDetail)
async def course(slug: str, db: DB):
    return await svc.course_detail(db, slug)


@router.get("/courses/{slug}/items", response_model=Page[ItemCard])
async def course_items(
    slug: str,
    db: DB,
    type: Literal["resource", "article", "collection", "question"] | None = None,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return await svc.course_items(db, slug, type, cursor, limit)


@router.get("/content/{item_id}/courses", response_model=list[CourseOut])
async def item_courses(item_id: uuid.UUID, db: DB, viewer: OptionalUser):
    item = not_found_unless_visible(viewer, await db.get(ContentItem, item_id))
    return await svc.item_courses(db, item.id)


@router.put(
    "/content/{item_id}/courses",
    response_model=list[CourseOut],
    dependencies=[Depends(limit_write)],
)
async def attach(item_id: uuid.UUID, body: AttachIn, db: DB, user: ActiveUser):
    item = await db.get(ContentItem, item_id)
    if item is None or not (item.status == "published" or can_manage(user, item)):
        raise NotFound("Not found.")
    if not can_manage(user, item):
        raise Forbidden("Only the author or an admin can file this under a course.")
    out = await svc.attach(db, item, body)
    await db.commit()
    return out


@router.post(
    "/programs",
    status_code=201,
    response_model=ProgramRef,
    dependencies=[Depends(limit_write)],
)
async def create_program(body: ProgramIn, db: DB, admin: AdminUser):
    row = await svc.create_program(db, admin, body)
    await db.commit()
    return row


@router.post(
    "/courses",
    status_code=201,
    response_model=CourseOut,
    dependencies=[Depends(limit_write)],
)
async def create_course(body: CourseIn, db: DB, admin: AdminUser):
    row = await svc.create_course(db, admin, body)
    await db.commit()
    return row


@router.put(
    "/courses/{slug}/path",
    response_model=CourseDetail,
    dependencies=[Depends(limit_write)],
)
async def set_path(slug: str, body: PathIn, db: DB, admin: AdminUser):
    out = await svc.set_path(db, admin, slug, body)
    await db.commit()
    return out
