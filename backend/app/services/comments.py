"""Comments on any content item: threaded one level, counted atomically on the item row."""

import uuid
from datetime import datetime

from sqlalchemy import delete, func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Forbidden, NotFound
from app.models.content import Comment, ContentItem, ContentStatus
from app.models.user import Role, User
from app.schemas.comments import CommentIn, CommentOut
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.models.qa import NotificationKind
from app.services import audit, notifications
from app.services.content import _lock_visible

MAX_REPLIES = 50  # per thread, so no list is ever unbounded


async def _published(db: AsyncSession, item_id: uuid.UUID) -> None:
    ok = await db.scalar(
        select(ContentItem.id).where(
            ContentItem.id == item_id,
            ContentItem.status == ContentStatus.published.value,
        )
    )
    if ok is None:
        raise NotFound("Not found.")


async def list_comments(
    db: AsyncSession, item_id: uuid.UUID, cursor: str | None, limit: int
) -> Page[CommentOut]:
    """Top-level comments oldest first, each with its replies (at most MAX_REPLIES)."""
    await _published(db, item_id)
    stmt = select(Comment).where(
        Comment.item_id == item_id, Comment.parent_id.is_(None)
    )
    if cursor:
        try:
            raw = decode_cursor(cursor)["k"]
            key = (datetime.fromisoformat(raw[0]), uuid.UUID(raw[1]))
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise AppError("Invalid cursor", code="invalid_cursor") from exc
        stmt = stmt.where(tuple_(Comment.created_at, Comment.id) > tuple_(*key))
    rows = list(
        (
            await db.execute(
                stmt.order_by(Comment.created_at, Comment.id).limit(limit + 1)
            )
        )
        .scalars()
        .all()
    )
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        nxt = encode_cursor({"k": [rows[-1].created_at.isoformat(), str(rows[-1].id)]})
    replies: dict[uuid.UUID, list[CommentOut]] = {}
    if rows:
        found = await db.execute(
            select(Comment)
            .where(Comment.parent_id.in_([r.id for r in rows]))
            .order_by(Comment.created_at, Comment.id)
        )
        for r in found.scalars():
            replies.setdefault(r.parent_id, []).append(  # type: ignore[arg-type]
                CommentOut.model_validate(r, from_attributes=True)
            )
    items = []
    for r in rows:
        out = CommentOut.model_validate(r, from_attributes=True)
        out.replies = replies.get(r.id, [])
        items.append(out)
    return Page(items=items, next_cursor=nxt)


async def create_comment(
    db: AsyncSession, user: User, item_id: uuid.UUID, data: CommentIn
) -> CommentOut:
    _, item_author, _ = await _lock_visible(
        db, item_id
    )  # serialises counter updates and the reply cap per item
    if data.parent_id:
        parent = await db.get(Comment, data.parent_id)
        if parent is None or parent.item_id != item_id:
            raise NotFound("The comment you are replying to is gone.")
        if parent.parent_id is not None:
            raise AppError(
                "Replies go one level deep: reply to the top comment instead.",
                code="reply_too_deep",
                status_code=422,
                fields={"parent_id": "Reply to a top-level comment"},
            )
        n = await db.scalar(select(func.count()).where(Comment.parent_id == parent.id))
        if (n or 0) >= MAX_REPLIES:
            raise AppError(
                "This thread is full. Start a new comment.",
                code="thread_full",
                status_code=409,
            )
    comment = Comment(
        id=uuid.uuid4(),
        item_id=item_id,
        parent_id=data.parent_id,
        author_id=user.id,
        author=user,
        body=data.body,
    )
    db.add(comment)
    await db.execute(
        update(ContentItem)
        .where(ContentItem.id == item_id)
        .values(comment_count=ContentItem.comment_count + 1)
    )
    await db.flush()
    for target in {item_author, parent.author_id if data.parent_id else item_author}:
        await notifications.notify(
            db,
            target,
            NotificationKind.reply,
            item_id,
            actor=user,
            message=data.body[:140],
        )
    await db.refresh(comment)  # server-side created_at
    return CommentOut.model_validate(comment, from_attributes=True)


async def delete_comment(db: AsyncSession, actor: User, comment_id: uuid.UUID) -> None:
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise NotFound("Not found.")
    if comment.author_id != actor.id and actor.role != Role.admin:
        raise Forbidden("Only the author or an admin can delete this.")
    await db.execute(  # same lock as create_comment, so counts cannot interleave
        select(ContentItem.id)
        .where(ContentItem.id == comment.item_id)
        .with_for_update()
    )
    gone = await db.execute(
        delete(Comment)
        .where((Comment.id == comment_id) | (Comment.parent_id == comment_id))
        .returning(Comment.id)
    )
    n = len(gone.all())
    await db.execute(
        update(ContentItem)
        .where(ContentItem.id == comment.item_id)
        .values(comment_count=ContentItem.comment_count - n)
    )
    if actor.id != comment.author_id:
        await audit.record(
            db,
            actor_id=actor.id,
            action="comment.delete",
            target_type="comment",
            target_id=comment_id,
            before={"body": comment.body[:200], "author_id": str(comment.author_id)},
            after={"deleted": n},
        )
    await db.flush()
