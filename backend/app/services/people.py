"""Profiles, the people directory, badges, contribution heatmap and the leaderboard."""

import uuid
from collections.abc import Callable

from sqlalchemy import func, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFound
from app.models.content import ContentItem, ContentStatus
from app.models.qa import Answer, ReputationEvent
from app.models.user import Role, User, UserStatus
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.schemas.library import (
    Badge,
    DayCount,
    ItemCard,
    LeaderRow,
    PersonCard,
    Profile,
    ProfilePatch,
)
from app.services.cards import card_page, published_cards


def listed(stmt):
    """Directory rule: confirmed emails only (keeps throwaway signups out) and never banned users."""
    return stmt.where(
        User.status != UserStatus.banned.value, User.email_verified_at.is_not(None)
    )


# slug -> (name, description, earned?). Badges are derived from counts on read, so they can
# never drift from the content; the trade-off is that they carry no "awarded on" date.
BADGES: list[tuple[str, str, str, Callable[[dict, User], bool]]] = [
    (
        "verified",
        "Verified Ufazian",
        "Confirmed as a UFAZ student or alumnus.",
        lambda c, u: u.role in (Role.verified_ufazian.value, Role.admin.value),
    ),
    ("first-find", "First find", "Shared a resource.", lambda c, u: c["resource"] >= 1),
    ("author", "In print", "Published an article.", lambda c, u: c["article"] >= 1),
    (
        "curator",
        "Curator",
        "Built a collection.",
        lambda c, u: c["collection"] >= 1,
    ),
    ("scholar", "Scholar", "Contributed to research.", lambda c, u: c["research"] >= 1),
    (
        "checked",
        "Checked",
        "Had an answer accepted.",
        lambda c, u: c["accepted_answers"] >= 1,
    ),
    (
        "prolific",
        "Prolific",
        "Ten published contributions.",
        lambda c, u: sum(
            c[t] for t in ("resource", "article", "collection", "question", "answer")
        )
        >= 10,
    ),
    ("regular", "Regular", "100 reputation.", lambda c, u: u.reputation >= 100),
    ("sage", "Sage", "500 reputation.", lambda c, u: u.reputation >= 500),
]


async def counts(db: AsyncSession, user_id: uuid.UUID) -> dict[str, int]:
    out = dict.fromkeys(
        ("resource", "article", "collection", "question", "answer"), 0
    ) | {"research": 0, "accepted_answers": 0}
    rows = await db.execute(
        select(ContentItem.type, func.count())
        .where(
            ContentItem.author_id == user_id,
            ContentItem.status == ContentStatus.published.value,
        )
        .group_by(ContentItem.type)
    )
    out.update({t: n for t, n in rows})
    out["research"] = await db.scalar(
        select(func.count()).where(
            ContentItem.author_id == user_id,
            ContentItem.status == ContentStatus.published.value,
            ContentItem.is_research.is_(True),
        )
    )
    out["accepted_answers"] = await db.scalar(
        select(func.count())
        .select_from(Answer)
        .where(
            ContentItem.author_id == user_id,
            ContentItem.status == ContentStatus.published.value,
            Answer.accepted_at.is_not(None),
        )
    )
    return out


async def activity(db: AsyncSession, user_id: uuid.UUID) -> list[DayCount]:
    """Published items and comments per UTC day over the last year (at most 366 rows)."""
    rows = await db.execute(
        text("""
            SELECT (t.at AT TIME ZONE 'UTC')::date AS day, count(*) AS n FROM (
              SELECT created_at AS at FROM content_items
                WHERE author_id = :u AND status = 'published'
              UNION ALL
              SELECT created_at FROM comments WHERE author_id = :u
            ) t
            WHERE t.at > now() - interval '365 days'
            GROUP BY 1 ORDER BY 1
            """),
        {"u": user_id},
    )
    return [DayCount(day=r.day, count=r.n) for r in rows]


async def visible_user(
    db: AsyncSession, user_id: uuid.UUID, viewer: User | None
) -> User:
    user = await db.get(User, user_id)
    if (
        user is not None
        and viewer is not None
        and (viewer.id == user.id or viewer.role == Role.admin.value)
    ):
        return user
    if (
        user is None
        or user.status == UserStatus.banned.value
        or user.email_verified_at is None
    ):
        raise NotFound("No such person.")
    return user


async def profile(db: AsyncSession, user: User) -> Profile:
    c = await counts(db, user.id)
    return Profile(
        **PersonCard.model_validate(user, from_attributes=True).model_dump(),
        bio=user.bio,
        socials=user.socials,
        joined_at=user.created_at,
        counts=c,
        badges=[
            Badge(slug=s, name=n, description=d)
            for s, n, d, ok in BADGES
            if ok(c, user)
        ],
        activity=await activity(db, user.id),
    )


async def update_profile(db: AsyncSession, user: User, data: ProfilePatch) -> Profile:
    changes = data.model_dump(exclude_unset=True, exclude={"socials"})
    for k, v in changes.items():
        if k != "graduation_year" and (
            v is None or (k == "display_name" and not v.strip())
        ):
            raise AppError(f"{k} cannot be empty", fields={k: "Required"})
        setattr(user, k, v.strip() if isinstance(v, str) else v)
    if data.socials is not None:
        user.socials = data.socials.model_dump(exclude_none=True)
    await db.flush()
    return await profile(db, user)


async def clear_avatar(db: AsyncSession, user: User) -> None:
    user.avatar_attachment_id = None
    await db.flush()


async def directory(
    db: AsyncSession,
    *,
    q: str | None,
    faculty: str | None,
    graduation_year: int | None,
    cursor: str | None,
    limit: int,
) -> Page[PersonCard]:
    """Top reputation first. Name search is a substring match (fine for a few thousand people)."""
    stmt = listed(select(User))
    if q:
        stmt = stmt.where(User.display_name.icontains(q.strip(), autoescape=True))
    if faculty:
        stmt = stmt.where(User.faculty == faculty)
    if graduation_year:
        stmt = stmt.where(User.graduation_year == graduation_year)
    if cursor:
        raw = decode_cursor(cursor).get("k")
        try:
            stmt = stmt.where(
                tuple_(User.reputation, User.id)
                < tuple_(int(raw[0]), uuid.UUID(raw[1]))
            )
        except (TypeError, ValueError, IndexError) as exc:
            raise AppError("Invalid cursor", code="invalid_cursor") from exc
    rows = (
        (
            await db.execute(
                stmt.order_by(User.reputation.desc(), User.id.desc()).limit(limit + 1)
            )
        )
        .scalars()
        .all()
    )
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        nxt = encode_cursor({"k": [rows[-1].reputation, str(rows[-1].id)]})
    return Page(
        items=[PersonCard.model_validate(u, from_attributes=True) for u in rows],
        next_cursor=nxt,
    )


async def contributions(
    db: AsyncSession, user_id: uuid.UUID, cursor: str | None, limit: int
) -> Page[ItemCard]:
    stmt = published_cards().where(ContentItem.author_id == user_id)
    return await card_page(db, stmt, ContentItem.created_at, cursor, limit)


async def leaderboard(db: AsyncSession, period: str, limit: int) -> list[LeaderRow]:
    """`all`: lifetime reputation. `month`: points earned since the 1st (UTC). Bounded top-N."""
    if period == "all":
        points = User.reputation
        stmt = listed(select(User, points.label("points"))).where(points > 0)
    else:
        points = func.sum(ReputationEvent.points)
        stmt = (
            listed(select(User, points.label("points")))
            .join(ReputationEvent, ReputationEvent.user_id == User.id)
            .where(
                ReputationEvent.created_at
                >= func.timezone(
                    "UTC", func.date_trunc("month", func.timezone("UTC", func.now()))
                )
            )
            .group_by(User.id)
            .having(points > 0)
        )
    rows = (
        await db.execute(stmt.order_by(text("points DESC"), User.id).limit(limit))
    ).all()
    return [
        LeaderRow(
            rank=i,
            points=r.points,
            person=PersonCard.model_validate(r[0], from_attributes=True),
        )
        for i, r in enumerate(rows, 1)
    ]
