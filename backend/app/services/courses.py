"""Programs, courses, attaching content to them, and the ordered "start here" path."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFound
from app.models.content import ContentItem, ContentStatus
from app.models.library import ContentCourse, Course, Program
from app.models.user import User
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
)
from app.services import audit
from app.services.cards import card_page, published_cards

MAX_PROGRAMS = 100  # admin-curated, tiny tables: bounded rather than paged
MAX_COURSES = 1000


async def list_programs(db: AsyncSession) -> list[ProgramOut]:
    programs = (
        (await db.execute(select(Program).order_by(Program.name).limit(MAX_PROGRAMS)))
        .scalars()
        .all()
    )
    courses = (
        (
            await db.execute(
                select(Course).order_by(Course.level, Course.name).limit(MAX_COURSES)
            )
        )
        .scalars()
        .all()
    )
    return [
        ProgramOut(
            slug=p.slug,
            name=p.name,
            description=p.description,
            courses=[
                CourseOut.model_validate(c, from_attributes=True)
                for c in courses
                if c.program_id == p.id
            ],
        )
        for p in programs
    ]


async def get_course(db: AsyncSession, slug: str) -> Course:
    course = (
        await db.execute(select(Course).where(Course.slug == slug))
    ).scalar_one_or_none()
    if course is None:
        raise NotFound("No such course.")
    return course


async def course_detail(db: AsyncSession, slug: str) -> CourseDetail:
    course = await get_course(db, slug)
    on_course = ContentCourse.course_id == course.id
    path = (
        (
            await db.execute(
                published_cards()
                .join(ContentCourse, ContentCourse.item_id == ContentItem.id)
                .where(on_course, ContentCourse.start_position.is_not(None))
                .order_by(ContentCourse.start_position)
            )
        )
        .scalars()
        .all()
    )
    count = await db.scalar(
        select(func.count())
        .select_from(ContentCourse)
        .join(ContentItem, ContentItem.id == ContentCourse.item_id)
        .where(
            on_course,
            ContentItem.status == ContentStatus.published.value,
            ContentItem.type != "answer",
        )
    )
    return CourseDetail(
        **CourseOut.model_validate(course, from_attributes=True).model_dump(),
        item_count=count or 0,
        start_here=[ItemCard.model_validate(i, from_attributes=True) for i in path],
    )


async def course_items(
    db: AsyncSession, slug: str, type: str | None, cursor: str | None, limit: int
) -> Page[ItemCard]:
    course = await get_course(db, slug)
    stmt = published_cards().join(
        ContentCourse,
        (ContentCourse.item_id == ContentItem.id)
        & (ContentCourse.course_id == course.id),
    )
    if type:
        stmt = stmt.where(ContentItem.type == type)
    return await card_page(db, stmt, ContentItem.created_at, cursor, limit)


async def item_courses(db: AsyncSession, item_id: uuid.UUID) -> list[CourseOut]:
    rows = (
        (
            await db.execute(
                select(Course)
                .join(ContentCourse, ContentCourse.course_id == Course.id)
                .where(ContentCourse.item_id == item_id)
                .order_by(Course.level, Course.name)
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    return [CourseOut.model_validate(c, from_attributes=True) for c in rows]


async def attach(
    db: AsyncSession, item: ContentItem, data: AttachIn
) -> list[CourseOut]:
    """Replace the item's courses. Items that stay keep their path position; dropped ones lose it."""
    if item.type == "answer":
        raise AppError("Answers belong to their question.", status_code=422)
    slugs = set(data.course_slugs)
    courses = (
        (await db.execute(select(Course).where(Course.slug.in_(slugs)))).scalars().all()
    )
    if len(courses) != len(slugs):
        raise AppError("Unknown course.", fields={"course_slugs": "Unknown course"})
    keep = {c.id for c in courses}
    current = {
        cid
        for (cid,) in await db.execute(
            select(ContentCourse.course_id).where(ContentCourse.item_id == item.id)
        )
    }
    for cid in current - keep:
        await db.delete(await db.get(ContentCourse, (item.id, cid)))
    for cid in keep - current:
        db.add(ContentCourse(item_id=item.id, course_id=cid))
    await db.flush()
    return await item_courses(db, item.id)


async def create_program(db: AsyncSession, admin: User, data: ProgramIn) -> Program:
    if await db.scalar(select(func.count()).select_from(Program)) >= MAX_PROGRAMS:
        raise AppError("Too many programs.", code="limit_reached", status_code=409)
    row = Program(**data.model_dump())
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise AppError(
            "That slug is taken.", code="slug_taken", status_code=409
        ) from exc
    await audit.record(
        db,
        actor_id=admin.id,
        action="program.create",
        target_type="program",
        target_id=row.id,
        after=data.model_dump(),
    )
    return row


async def create_course(db: AsyncSession, admin: User, data: CourseIn) -> Course:
    if await db.scalar(select(func.count()).select_from(Course)) >= MAX_COURSES:
        raise AppError("Too many courses.", code="limit_reached", status_code=409)
    program = (
        await db.execute(select(Program).where(Program.slug == data.program_slug))
    ).scalar_one_or_none()
    if program is None:
        raise AppError("Unknown program.", fields={"program_slug": "Unknown program"})
    row = Course(program_id=program.id, **data.model_dump(exclude={"program_slug"}))
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise AppError(
            "That slug is taken.", code="slug_taken", status_code=409
        ) from exc
    await audit.record(
        db,
        actor_id=admin.id,
        action="course.create",
        target_type="course",
        target_id=row.id,
        after=data.model_dump(),
    )
    await db.refresh(row)
    return row


async def set_path(
    db: AsyncSession, admin: User, slug: str, data: PathIn
) -> CourseDetail:
    """Replace the start-here path. Listed items are attached to the course if they were not."""
    course = await get_course(db, slug)
    ids = list(dict.fromkeys(data.item_ids))
    ok = set(
        (
            await db.execute(
                select(ContentItem.id).where(
                    ContentItem.id.in_(ids),
                    ContentItem.status == ContentStatus.published.value,
                    ContentItem.type != "answer",
                )
            )
        )
        .scalars()
        .all()
    )
    if ok != set(ids):
        raise AppError(
            "Only published resources, articles, collections and questions can join the path.",
            fields={"item_ids": "Unknown or unpublished item"},
        )
    before = list(
        (
            await db.execute(
                select(ContentCourse.item_id)
                .where(
                    ContentCourse.course_id == course.id,
                    ContentCourse.start_position.is_not(None),
                )
                .order_by(ContentCourse.start_position)
            )
        )
        .scalars()
        .all()
    )
    await db.execute(
        update(ContentCourse)
        .where(ContentCourse.course_id == course.id)
        .values(start_position=None)
    )
    for pos, item_id in enumerate(ids, 1):
        await db.execute(
            pg_insert(ContentCourse)
            .values(item_id=item_id, course_id=course.id, start_position=pos)
            .on_conflict_do_update(
                index_elements=["item_id", "course_id"], set_={"start_position": pos}
            )
        )
    await audit.record(
        db,
        actor_id=admin.id,
        action="course.path",
        target_type="course",
        target_id=course.id,
        before={"path": before},
        after={"path": ids},
    )
    return await course_detail(db, slug)
