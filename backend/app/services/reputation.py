"""Reputation: a points table in code, an idempotent ledger, privileges by threshold.

Every award has an `event_key` ("vote:<voter>:<item>", "accept:<answer>"), unique per user, so
repeating or flipping an event rewrites one ledger row instead of stacking points.
`users.reputation` is moved by the same delta in the same transaction, so it always equals the
ledger sum. Vote points are capped per rolling day; accepting an answer is not.
"""

import uuid
from datetime import datetime

from sqlalchemy import delete, func, select, text, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, Forbidden
from app.models.content import ContentItem
from app.models.qa import ReputationEvent, ReputationReason
from app.models.user import Role, User
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.schemas.reputation import (
    PointRule,
    PrivilegeRule,
    ReputationEventOut,
    ReputationRules,
)

# Points an author earns when their content type is upvoted.
UPVOTE_POINTS = {
    "resource": 5,
    "article": 5,
    "collection": 3,
    "question": 5,
    "answer": 10,
}
DOWNVOTE_POINTS = -2
ANSWER_ACCEPTED_POINTS = 15  # the answerer
ACCEPTED_ANSWER_POINTS = (
    2  # the asker who accepted (never for accepting your own answer)
)

PRIVILEGES = {
    "downvote_answers": (15, "Downvote answers"),
    "mark_duplicate": (100, "Mark any question as a duplicate"),
}


def has_privilege(user: User, name: str) -> bool:
    return user.role == Role.admin or user.reputation >= PRIVILEGES[name][0]


def require_privilege(user: User, name: str) -> None:
    if not has_privilege(user, name):
        need, label = PRIVILEGES[name]
        raise Forbidden(
            f"“{label}” unlocks at {need} reputation.", code="privilege_required"
        )


def rules() -> ReputationRules:
    pts = [
        PointRule(reason=f"upvote_{t}", label=f"Your {t} is upvoted", points=p)
        for t, p in UPVOTE_POINTS.items()
    ]
    pts += [
        PointRule(
            reason="downvote", label="Your post is downvoted", points=DOWNVOTE_POINTS
        ),
        PointRule(
            reason=ReputationReason.answer_accepted.value,
            label="Your answer is accepted",
            points=ANSWER_ACCEPTED_POINTS,
        ),
        PointRule(
            reason=ReputationReason.accepted_answer.value,
            label="You accept someone else's answer",
            points=ACCEPTED_ANSWER_POINTS,
        ),
    ]
    return ReputationRules(
        points=pts,
        privileges=[
            PrivilegeRule(key=k, label=label, threshold=n)
            for k, (n, label) in PRIVILEGES.items()
        ],
        daily_vote_cap=settings.REP_DAILY_CAP,
    )


async def _set(
    db: AsyncSession,
    user_id: uuid.UUID,
    key: str,
    reason: ReputationReason,
    points: int,
    item_id: uuid.UUID | None,
) -> None:
    """Make the ledger say `points` for this event (0 removes it) and move the total by the difference."""
    row = (
        await db.execute(
            select(ReputationEvent)
            .where(ReputationEvent.user_id == user_id, ReputationEvent.event_key == key)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if reason == ReputationReason.vote_up and points > 0:
        earned = await db.scalar(
            select(func.coalesce(func.sum(ReputationEvent.points), 0)).where(
                ReputationEvent.user_id == user_id,
                ReputationEvent.reason == ReputationReason.vote_up.value,
                ReputationEvent.event_key != key,
                ReputationEvent.created_at > func.now() - text("interval '1 day'"),
            )
        )
        points = max(min(points, settings.REP_DAILY_CAP - (earned or 0)), 0)
    old = row.points if row else 0
    if points == 0:
        if row:
            await db.execute(
                delete(ReputationEvent).where(ReputationEvent.id == row.id)
            )
    elif row:
        row.points, row.reason = points, reason.value
    else:
        db.add(
            ReputationEvent(
                user_id=user_id,
                event_key=key,
                reason=reason.value,
                points=points,
                item_id=item_id,
            )
        )
    if points != old:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(reputation=User.reputation + points - old)
        )
    await db.flush()


async def on_vote(
    db: AsyncSession,
    voter: User,
    author_id: uuid.UUID,
    item_type: str,
    item_id: uuid.UUID,
    value: int,
) -> None:
    """Call under the item's row lock. Self-votes never get here (cast_vote rejects them)."""
    reason = ReputationReason.vote_up if value == 1 else ReputationReason.vote_down
    points = {1: UPVOTE_POINTS[item_type], -1: DOWNVOTE_POINTS, 0: 0}[value]
    await _set(db, author_id, f"vote:{voter.id}:{item_id}", reason, points, item_id)


async def on_accept(
    db: AsyncSession,
    answer_id: uuid.UUID,
    answerer_id: uuid.UUID,
    asker_id: uuid.UUID,
    on: bool,
) -> None:
    """Award (or take back) the acceptance points; accepting your own answer earns nothing."""
    if answerer_id == asker_id:
        return
    await _set(
        db,
        answerer_id,
        f"accept:{answer_id}",
        ReputationReason.answer_accepted,
        ANSWER_ACCEPTED_POINTS if on else 0,
        answer_id,
    )
    await _set(
        db,
        asker_id,
        f"accepting:{answer_id}",
        ReputationReason.accepted_answer,
        ACCEPTED_ANSWER_POINTS if on else 0,
        answer_id,
    )


async def history(
    db: AsyncSession, user: User, cursor: str | None, limit: int
) -> Page[ReputationEventOut]:
    stmt = (
        select(ReputationEvent, ContentItem.call_number, ContentItem.title)
        .outerjoin(ContentItem, ContentItem.id == ReputationEvent.item_id)
        .where(ReputationEvent.user_id == user.id)
    )
    if cursor:
        try:
            raw = decode_cursor(cursor)["k"]
            key = (datetime.fromisoformat(raw[0]), uuid.UUID(raw[1]))
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise AppError("Invalid cursor", code="invalid_cursor") from exc
        stmt = stmt.where(
            tuple_(ReputationEvent.created_at, ReputationEvent.id) < tuple_(*key)
        )
    rows = (
        await db.execute(
            stmt.order_by(
                ReputationEvent.created_at.desc(), ReputationEvent.id.desc()
            ).limit(limit + 1)
        )
    ).all()
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1][0]
        nxt = encode_cursor({"k": [last.created_at.isoformat(), str(last.id)]})
    return Page(
        items=[
            ReputationEventOut(
                reason=e.reason,
                points=e.points,
                call_number=cn,
                title=t,
                created_at=e.created_at,
            )
            for e, cn, t in rows
        ],
        next_cursor=nxt,
    )
