"""Questions, answers, accepted/pinned answers, duplicate merging and similar-question lookup."""

import uuid
from datetime import datetime

from sqlalchemy import case, func, select, text, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.permissions import initial_status
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.models.content import (
    ContentItem,
    ContentStatus,
    ContentType,
    Resource,
    Tag,
)
from app.models.qa import Answer, NotificationKind, Question
from app.models.user import Role, User
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.schemas.qa import (
    AnswerIn,
    AnswerOut,
    ItemRef,
    QuestionIn,
    QuestionOut,
    SimilarHit,
)
from app.services import audit, notifications, reputation
from app.services import content as base

PUBLISHED = ContentStatus.published.value


# --- questions --------------------------------------------------------------------------


async def _stats(
    db: AsyncSession, ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, bool]]:
    """question id -> (published answers, has an accepted one)."""
    a = aliased(Answer)
    rows = await db.execute(
        select(a.question_id, func.count(), func.bool_or(a.accepted_at.is_not(None)))
        .select_from(a)
        .where(a.question_id.in_(ids), a.status == PUBLISHED)
        .group_by(a.question_id)
    )
    return {q: (n, bool(acc)) for q, n, acc in rows.all()}


async def _refs(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, ItemRef]:
    if not ids:
        return {}
    rows = await db.execute(
        select(ContentItem.id, ContentItem.call_number, ContentItem.title).where(
            ContentItem.id.in_(ids), ContentItem.status == PUBLISHED
        )
    )
    return {r.id: ItemRef(call_number=r.call_number, title=r.title) for r in rows}


async def present(
    db: AsyncSession, viewer: User | None, items: list[Question]
) -> list[QuestionOut]:
    ids = [i.id for i in items]
    votes, marks = await base.viewer_state(db, viewer, ids)
    stats = await _stats(db, ids) if ids else {}
    refs = await _refs(
        db,
        {r for i in items for r in (i.linked_resource_id, i.duplicate_of_id) if r},
    )
    out = []
    for i in items:
        o = QuestionOut.model_validate(i, from_attributes=True)
        o.answer_count, o.has_accepted = stats.get(i.id, (0, False))
        o.linked_resource = refs.get(i.linked_resource_id)  # type: ignore[arg-type]
        o.duplicate_of = refs.get(i.duplicate_of_id)  # type: ignore[arg-type]
        out.append(base.decorate(o, i, viewer, votes, marks))
    return out


async def create_question(db: AsyncSession, user: User, data: QuestionIn) -> Question:
    linked = None
    if data.linked_resource:
        linked = await db.scalar(
            select(Resource.id).where(
                Resource.call_number == data.linked_resource.upper(),
                Resource.status == PUBLISHED,
            )
        )
        if linked is None:
            raise AppError(
                "That resource does not exist.",
                fields={
                    "linked_resource": "No published resource with this call number"
                },
            )
    item = Question(
        id=uuid.uuid4(),
        author_id=user.id,
        author=user,
        status=initial_status(user),
        call_number=await base._call_number(db, ContentType.question),
        title=data.title,
        description=data.body,
        topic=data.topic,
        linked_resource_id=linked,
        tags=await base._tags(db, data.tags),
    )
    db.add(item)
    await db.flush()
    return await base.load_item(db, Question, id=item.id)  # type: ignore[return-value]


async def list_questions(
    db: AsyncSession,
    viewer: User | None,
    *,
    sort: str,
    topic: str | None,
    tag: str | None,
    unanswered: bool,
    cursor: str | None,
    limit: int,
) -> Page[QuestionOut]:
    stmt = select(Question).where(Question.status == PUBLISHED)
    if topic:
        stmt = stmt.where(func.lower(Question.topic) == topic.lower())
    if tag:
        stmt = stmt.where(Question.tags.any(Tag.slug == tag))
    if unanswered:
        a = aliased(Answer)
        stmt = stmt.where(
            ~select(a.id)
            .select_from(a)
            .where(a.question_id == Question.id, a.status == PUBLISHED)
            .exists()
        )
    rows, nxt = await base.keyset_page(db, stmt, Question, sort, cursor, limit)
    return Page(items=await present(db, viewer, rows), next_cursor=nxt)


async def similar(db: AsyncSession, title: str) -> list[SimilarHit]:
    """Existing questions that look like the one being typed (typo-tolerant, duplicates excluded)."""
    await db.execute(
        text("SELECT set_config('pg_trgm.similarity_threshold', '0.3', true)")
    )
    rows = (
        await db.execute(
            text(
                "SELECT ci.id, ci.call_number, ci.title FROM content_items ci "
                "JOIN questions q ON q.id = ci.id "
                "WHERE ci.status = 'published' AND q.duplicate_of_id IS NULL "
                "AND (f_unaccent(lower(ci.title)) % f_unaccent(lower(:t)) "
                "     OR ci.search_vector @@ plainto_tsquery('ufaz_search', :t)) "
                "ORDER BY similarity(f_unaccent(lower(ci.title)), f_unaccent(lower(:t))) DESC, "
                "ci.created_at DESC LIMIT 5"
            ),
            {"t": title.strip()},
        )
    ).all()
    stats = await _stats(db, [r.id for r in rows]) if rows else {}
    return [
        SimilarHit(
            call_number=r.call_number,
            title=r.title,
            answer_count=stats.get(r.id, (0, False))[0],
            has_accepted=stats.get(r.id, (0, False))[1],
        )
        for r in rows
    ]


# --- answers ----------------------------------------------------------------------------


def _flag():
    """2 for the accepted answer, 1 for a pinned one: accepted sorts first."""
    return case((Answer.accepted_at.is_not(None), 2), else_=0) + case(
        (Answer.pinned_at.is_not(None), 1), else_=0
    )


async def present_answers(
    db: AsyncSession, viewer: User | None, rows: list[Answer]
) -> list[AnswerOut]:
    votes, _ = await base.viewer_state(db, viewer, [r.id for r in rows])
    return [
        base.decorate(
            AnswerOut.model_validate(r, from_attributes=True), r, viewer, votes, set()
        )
        for r in rows
    ]


async def list_answers(
    db: AsyncSession,
    viewer: User | None,
    question_id: uuid.UUID,
    cursor: str | None,
    limit: int,
) -> Page[AnswerOut]:
    """Accepted first, then pinned, then by votes. Your own unpublished answers show to you."""
    stmt = select(Answer).where(Answer.question_id == question_id)
    if viewer is None or viewer.role != Role.admin:
        mine = Answer.author_id == viewer.id if viewer else False
        stmt = stmt.where((Answer.status == PUBLISHED) | mine)
    flag = _flag()
    keys = (flag, Answer.vote_score, Answer.created_at, Answer.id)
    if cursor:
        try:
            raw = decode_cursor(cursor)["k"]
            vals = (
                int(raw[0]),
                int(raw[1]),
                datetime.fromisoformat(raw[2]),
                uuid.UUID(raw[3]),
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise AppError("Invalid cursor", code="invalid_cursor") from exc
        stmt = stmt.where(tuple_(*keys) < tuple_(*vals))
    rows = list(
        (await db.execute(stmt.order_by(*[k.desc() for k in keys]).limit(limit + 1)))
        .scalars()
        .all()
    )
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        nxt = encode_cursor(
            {
                "k": [
                    (2 if last.accepted else 0) + (1 if last.pinned else 0),
                    last.vote_score,
                    last.created_at.isoformat(),
                    str(last.id),
                ]
            }
        )
    return Page(items=await present_answers(db, viewer, rows), next_cursor=nxt)


async def create_answer(
    db: AsyncSession, user: User, question: Question, data: AnswerIn
) -> Answer:
    await base._lock_visible(db, question.id)  # 404 unless the question is published
    if question.duplicate_of_id:
        raise Conflict(
            "This question was merged into another. Answer the original.",
            code="question_merged",
        )
    item = Answer(
        id=uuid.uuid4(),
        author_id=user.id,
        author=user,
        status=initial_status(user),
        call_number=await base._call_number(db, ContentType.answer),
        title=question.title,
        description=data.body,
        question_id=question.id,
    )
    db.add(item)
    await db.flush()
    if item.status == PUBLISHED:
        await notifications.notify(
            db, question.author_id, NotificationKind.answer, item.id, actor=user
        )
    return await base.load_item(db, Answer, id=item.id)  # type: ignore[return-value]


async def _published_answer(db: AsyncSession, answer_id: uuid.UUID) -> Answer:
    answer = await base.load_item(db, Answer, id=answer_id)
    if answer is None or answer.status != PUBLISHED:
        raise NotFound("Not found.")
    return answer


async def set_accepted(
    db: AsyncSession, user: User, answer_id: uuid.UUID, on: bool
) -> AnswerOut:
    """Only the asker accepts. Accepting another answer moves the tick (and the points) along."""
    answer = await _published_answer(db, answer_id)
    await base._lock_visible(db, answer.question_id)
    question = await base.load_item(db, Question, id=answer.question_id)
    assert question is not None
    if question.author_id != user.id:
        raise Forbidden("Only the asker can accept an answer.", code="not_asker")
    if on and not answer.accepted_at:
        prev = (
            await db.execute(
                select(Answer).where(
                    Answer.question_id == question.id, Answer.accepted_at.is_not(None)
                )
            )
        ).scalar_one_or_none()
        if prev:
            prev.accepted_at = None
            await reputation.on_accept(
                db, prev.id, prev.author_id, question.author_id, False
            )
            await db.flush()
        answer.accepted_at = func.now()  # type: ignore[assignment]
        await reputation.on_accept(
            db, answer.id, answer.author_id, question.author_id, True
        )
        await notifications.notify(
            db,
            answer.author_id,
            NotificationKind.answer_accepted,
            answer.id,
            actor=user,
            dedupe_key=f"accepted:{answer.id}",
        )
    elif not on and answer.accepted_at:
        answer.accepted_at = None
        await reputation.on_accept(
            db, answer.id, answer.author_id, question.author_id, False
        )
    await db.flush()
    answer = await base.load_item(db, Answer, id=answer_id)  # type: ignore[assignment]
    return (await present_answers(db, user, [answer]))[0]


async def set_pinned(
    db: AsyncSession, admin: User, answer_id: uuid.UUID, on: bool
) -> AnswerOut:
    answer = await _published_answer(db, answer_id)
    await base._lock_visible(db, answer.question_id)
    if on and not answer.pinned_at:
        prev = (
            await db.execute(
                select(Answer).where(
                    Answer.question_id == answer.question_id,
                    Answer.pinned_at.is_not(None),
                )
            )
        ).scalar_one_or_none()
        if prev:
            prev.pinned_at = None
            await db.flush()
        answer.pinned_at = func.now()  # type: ignore[assignment]
        await notifications.notify(
            db,
            answer.author_id,
            NotificationKind.moderation,
            answer.id,
            actor=admin,
            message="your answer was pinned",
        )
    elif not on:
        answer.pinned_at = None
    await audit.record(
        db,
        actor_id=admin.id,
        action="answer.pin" if on else "answer.unpin",
        target_type="content_item",
        target_id=answer.id,
    )
    await db.flush()
    answer = await base.load_item(db, Answer, id=answer_id)  # type: ignore[assignment]
    return (await present_answers(db, admin, [answer]))[0]


# --- duplicates ------------------------------------------------------------------------------


def _may_merge(user: User, question: Question) -> None:
    if user.id != question.author_id:
        reputation.require_privilege(user, "mark_duplicate")


async def mark_duplicate(
    db: AsyncSession, user: User, question: Question, of: str
) -> None:
    """Point `question` at its original; anything already pointing at it follows along (no chains)."""
    await base._lock_visible(db, question.id)
    _may_merge(user, question)
    target = await base.load_item(db, Question, call_number=of.upper())
    bad = None
    if target is None or target.status != PUBLISHED:
        bad = "No published question with this call number"
    elif target.id == question.id:
        bad = "A question cannot duplicate itself"
    elif target.duplicate_of_id:
        bad = "That question is itself a duplicate; pick the original"
    if bad:
        raise AppError(bad, fields={"of": bad}, status_code=422)
    assert target is not None
    before = question.duplicate_of_id
    await db.execute(
        update(Question.__table__)
        .where(Question.__table__.c.duplicate_of_id == question.id)
        .values(duplicate_of_id=target.id)
    )
    question.duplicate_of_id = target.id
    await _after_merge(db, user, question, before, target.id)


async def unmark_duplicate(db: AsyncSession, user: User, question: Question) -> None:
    _may_merge(user, question)
    before, question.duplicate_of_id = question.duplicate_of_id, None
    await _after_merge(db, user, question, before, None)


async def _after_merge(db, user, question, before, after) -> None:
    if user.id != question.author_id:
        await audit.record(
            db,
            actor_id=user.id,
            action="question.duplicate",
            target_type="content_item",
            target_id=question.id,
            before={"duplicate_of_id": before},
            after={"duplicate_of_id": after},
        )
        await notifications.notify(
            db,
            question.author_id,
            NotificationKind.moderation,
            question.id,
            actor=user,
            message="marked as a duplicate" if after else "duplicate mark removed",
        )
    await db.flush()
