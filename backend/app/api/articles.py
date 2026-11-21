import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB
from app.api.permissions import (
    ActiveUser,
    OptionalUser,
    VerifiedUser,
    can_manage,
    not_found_unless_visible,
)
from app.core.errors import Forbidden, NotFound
from app.core.ratelimit import limit_write
from app.models.content import Article, ContentStatus
from app.schemas.articles import (
    ArticleCard,
    ArticleIn,
    ArticleOut,
    ArticlePatch,
    PreviewIn,
    PreviewOut,
)
from app.schemas.common import Page
from app.services import articles as svc

router = APIRouter(tags=["articles"])

Limit = Annotated[int, Query(ge=1, le=50)]
Cursor = Annotated[str | None, Query(max_length=512)]


@router.get("/articles", response_model=Page[ArticleCard])
async def list_articles(
    db: DB,
    viewer: OptionalUser,
    sort: Literal["latest", "top"] = "latest",
    tag: Annotated[str | None, Query(max_length=48)] = None,
    research: bool | None = None,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    return await svc.list_articles(
        db,
        viewer,
        sort=sort,
        tag=tag,
        research=research,
        mine=None,
        cursor=cursor,
        limit=limit,
    )


@router.get("/me/articles", response_model=Page[ArticleCard])
async def my_articles(
    db: DB, user: ActiveUser, cursor: Cursor = None, limit: Limit = 20
):
    """Your own articles in every state, drafts included."""
    return await svc.list_articles(
        db,
        user,
        sort="latest",
        tag=None,
        research=None,
        mine=user,
        cursor=cursor,
        limit=limit,
    )


@router.post(
    "/articles/preview",
    response_model=PreviewOut,
    dependencies=[Depends(limit_write)],
)
async def preview(body: PreviewIn, user: ActiveUser):
    """Render Markdown exactly as it will be published (same sanitizer), for the editor."""
    return svc.preview(body.body_md)


@router.get("/articles/{ref}", response_model=ArticleOut)
async def get_article(ref: str, db: DB, viewer: OptionalUser):
    item = not_found_unless_visible(viewer, await svc.find(db, ref))
    return (await svc.present(db, viewer, [item], full=True))[0]  # type: ignore[list-item]


@router.post(
    "/articles",
    status_code=201,
    response_model=ArticleOut,
    dependencies=[Depends(limit_write)],
)
async def create_article(body: ArticleIn, db: DB, user: VerifiedUser):
    item = await svc.create(db, user, body)
    await db.commit()
    return (await svc.present(db, user, [item], full=True))[0]


@router.patch(
    "/articles/{item_id}",
    response_model=ArticleOut,
    dependencies=[Depends(limit_write)],
)
async def update_article(
    item_id: uuid.UUID, body: ArticlePatch, db: DB, user: ActiveUser
):
    item = await svc.base.load_item(db, Article, id=item_id)
    if item is None or not (
        item.status == ContentStatus.published or can_manage(user, item)
    ):
        raise NotFound("Not found.")
    if not can_manage(user, item):
        raise Forbidden("Only the author or an admin can edit this.")
    item = await svc.update(db, user, item, body)
    await db.commit()
    return (await svc.present(db, user, [item], full=True))[0]
