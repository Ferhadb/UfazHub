import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import DB
from app.api.permissions import ActiveUser, OptionalUser
from app.core.ratelimit import limit_search, limit_write
from app.schemas.common import Page
from app.schemas.library import ItemCard, LeaderRow, PersonCard, Profile, ProfilePatch
from app.services import people as svc

router = APIRouter(tags=["people"])

Cursor = Annotated[str | None, Query(max_length=512)]
Limit = Annotated[int, Query(ge=1, le=50)]


@router.get(
    "/people", response_model=Page[PersonCard], dependencies=[Depends(limit_search)]
)
async def directory(
    db: DB,
    q: Annotated[str | None, Query(max_length=60)] = None,
    faculty: Annotated[str | None, Query(max_length=80)] = None,
    graduation_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    cursor: Cursor = None,
    limit: Limit = 24,
):
    return await svc.directory(
        db,
        q=q,
        faculty=faculty,
        graduation_year=graduation_year,
        cursor=cursor,
        limit=limit,
    )


@router.get("/people/by-gpa/{gpa_id}")
async def person_by_gpa(gpa_id: Annotated[str, Path(max_length=32)], db: DB):
    return {"id": await svc.id_by_gpa(db, gpa_id)}


@router.get("/people/{user_id}", response_model=Profile)
async def person(user_id: uuid.UUID, db: DB, viewer: OptionalUser):
    return await svc.profile(db, await svc.visible_user(db, user_id, viewer))


@router.get("/people/{user_id}/contributions", response_model=Page[ItemCard])
async def contributions(
    user_id: uuid.UUID,
    db: DB,
    viewer: OptionalUser,
    cursor: Cursor = None,
    limit: Limit = 12,
):
    user = await svc.visible_user(db, user_id, viewer)
    return await svc.contributions(db, user.id, cursor, limit)


@router.patch(
    "/me/profile", response_model=Profile, dependencies=[Depends(limit_write)]
)
async def update_profile(body: ProfilePatch, db: DB, user: ActiveUser):
    out = await svc.update_profile(db, user, body)
    await db.commit()
    return out


@router.delete("/me/avatar", status_code=204, dependencies=[Depends(limit_write)])
async def remove_avatar(db: DB, user: ActiveUser):
    await svc.clear_avatar(db, user)
    await db.commit()


@router.get("/leaderboard", response_model=list[LeaderRow])
async def leaderboard(
    db: DB,
    period: Literal["month", "all"] = "month",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """Bounded top-N, so there is no next page."""
    return await svc.leaderboard(db, period, limit)


@router.get("/leaderboard/contributor-of-the-month", response_model=LeaderRow | None)
async def contributor_of_the_month(db: DB):
    rows = await svc.leaderboard(db, "month", 1)
    return rows[0] if rows else None
