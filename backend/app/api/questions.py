import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB
from app.api.permissions import (
    ActiveUser,
    AdminUser,
    OptionalUser,
    VerifiedUser,
    not_found_unless_visible,
)
from app.core.errors import NotFound
from app.core.ratelimit import limit_search, limit_write
from app.models.qa import Question
from app.schemas.common import Page
from app.schemas.qa import (
    AnswerIn,
    AnswerOut,
    DuplicateIn,
    QuestionIn,
    QuestionOut,
    SimilarHit,
)
from app.services import content as base
from app.services import qa as svc

router = APIRouter(tags=["questions"])

Limit = Annotated[int, Query(ge=1, le=50)]
Cursor = Annotated[str | None, Query(max_length=512)]


async def _question(db, item_id: uuid.UUID) -> Question:
    q = await base.load_item(db, Question, id=item_id)
    if q is None:
        raise NotFound("Not found.")
    return q


@router.get("/questions", response_model=Page[QuestionOut])
async def list_questions(
    db: DB,
    viewer: OptionalUser,
    sort: Literal["latest", "top"] = "latest",
    topic: Annotated[str | None, Query(max_length=60)] = None,
    tag: Annotated[str | None, Query(max_length=48)] = None,
    unanswered: bool = False,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    return await svc.list_questions(
        db,
        viewer,
        sort=sort,
        topic=topic,
        tag=tag,
        unanswered=unanswered,
        cursor=cursor,
        limit=limit,
    )


@router.get(
    "/questions/similar",
    response_model=list[SimilarHit],
    dependencies=[Depends(limit_search)],
)
async def similar(db: DB, title: Annotated[str, Query(min_length=4, max_length=200)]):
    """Suggestions shown while the asker types a title."""
    return await svc.similar(db, title)


@router.get("/questions/{call_number}", response_model=QuestionOut)
async def get_question(call_number: str, db: DB, viewer: OptionalUser):
    item = await base.load_item(db, Question, call_number=call_number.upper())
    item = not_found_unless_visible(viewer, item)
    return (await svc.present(db, viewer, [item]))[0]  # type: ignore[list-item]


@router.post(
    "/questions",
    status_code=201,
    response_model=QuestionOut,
    dependencies=[Depends(limit_write)],
)
async def ask(body: QuestionIn, db: DB, user: VerifiedUser):
    item = await svc.create_question(db, user, body)
    await db.commit()
    return (await svc.present(db, user, [item]))[0]


@router.get("/questions/{call_number}/answers", response_model=Page[AnswerOut])
async def list_answers(
    call_number: str,
    db: DB,
    viewer: OptionalUser,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    q = await base.load_item(db, Question, call_number=call_number.upper())
    q = not_found_unless_visible(viewer, q)
    return await svc.list_answers(db, viewer, q.id, cursor, limit)


@router.post(
    "/questions/{item_id}/answers",
    status_code=201,
    response_model=AnswerOut,
    dependencies=[Depends(limit_write)],
)
async def answer(item_id: uuid.UUID, body: AnswerIn, db: DB, user: VerifiedUser):
    q = await _question(db, item_id)
    item = await svc.create_answer(db, user, q, body)
    await db.commit()
    return (await svc.present_answers(db, user, [item]))[0]


@router.put(
    "/questions/{item_id}/duplicate",
    status_code=204,
    dependencies=[Depends(limit_write)],
)
async def mark_duplicate(
    item_id: uuid.UUID, body: DuplicateIn, db: DB, user: ActiveUser
):
    await svc.mark_duplicate(db, user, await _question(db, item_id), body.of)
    await db.commit()


@router.delete(
    "/questions/{item_id}/duplicate",
    status_code=204,
    dependencies=[Depends(limit_write)],
)
async def unmark_duplicate(item_id: uuid.UUID, db: DB, user: ActiveUser):
    await svc.unmark_duplicate(db, user, await _question(db, item_id))
    await db.commit()


@router.put(
    "/answers/{answer_id}/accept",
    response_model=AnswerOut,
    dependencies=[Depends(limit_write)],
)
async def accept(answer_id: uuid.UUID, db: DB, user: ActiveUser):
    out = await svc.set_accepted(db, user, answer_id, True)
    await db.commit()
    return out


@router.delete(
    "/answers/{answer_id}/accept",
    response_model=AnswerOut,
    dependencies=[Depends(limit_write)],
)
async def unaccept(answer_id: uuid.UUID, db: DB, user: ActiveUser):
    out = await svc.set_accepted(db, user, answer_id, False)
    await db.commit()
    return out


@router.put(
    "/answers/{answer_id}/pin",
    response_model=AnswerOut,
    dependencies=[Depends(limit_write)],
)
async def pin(answer_id: uuid.UUID, db: DB, admin: AdminUser):
    out = await svc.set_pinned(db, admin, answer_id, True)
    await db.commit()
    return out


@router.delete(
    "/answers/{answer_id}/pin",
    response_model=AnswerOut,
    dependencies=[Depends(limit_write)],
)
async def unpin(answer_id: uuid.UUID, db: DB, admin: AdminUser):
    out = await svc.set_pinned(db, admin, answer_id, False)
    await db.commit()
    return out
