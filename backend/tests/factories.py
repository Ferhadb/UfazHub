"""Test helpers: users with any role/status and ready-made bearer headers."""

import uuid
from datetime import UTC, datetime

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.user import User


async def make_user(
    role: str = "user",
    status: str = "active",
    verified: bool = True,
    name: str = "Test User",
) -> tuple[User, dict]:
    async with SessionLocal() as db:
        user = User(
            email=f"u{uuid.uuid4().hex[:12]}@example.com",
            display_name=name,
            password_hash="x",
            role=role,
            status=status,
            email_verified_at=datetime.now(UTC) if verified else None,
        )
        db.add(user)
        await db.commit()
    token, _ = create_access_token(str(user.id), user.role)
    return user, {"Authorization": f"Bearer {token}"}


def resource_payload(**over) -> dict:
    base = {
        "title": "Linear Algebra Done Right",
        "description": "A proof-first textbook that pairs well with the L2 algebra course.",
        "resource_type": "book",
        "category": "Mathematics",
        "difficulty": "intermediate",
        "time_commitment_minutes": 600,
        "links": [{"url": f"https://example.org/{uuid.uuid4().hex}", "label": "PDF"}],
        "tags": ["algebra"],
    }
    return {**base, **over}


async def make_resource(client, headers, **over) -> dict:
    """Create a resource as a trusted user (publishes immediately)."""
    r = await client.post(
        "/api/resources", json=resource_payload(**over), headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()


def article_payload(**over) -> dict:
    base = {
        "title": "How I survived the Algorithms exam",
        "body_md": "## Start early\n\nSolve one problem a day. " * 3
        + "\n\n### Tools\n\nA pencil.",
        "tags": ["algorithms"],
        "publish": True,
    }
    return {**base, **over}


async def make_article(client, headers, **over) -> dict:
    r = await client.post(
        "/api/articles", json=article_payload(**over), headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()


def png_bytes(size=(40, 30), color=(200, 30, 30)) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def question_payload(**over) -> dict:
    base = {
        "title": "How do I prove Dijkstra's algorithm is correct?",
        "body": "I follow the steps but the invariant proof loses me. Where should I start?",
        "topic": "Algorithms",
        "tags": ["algorithms"],
    }
    return {**base, **over}


async def make_question(client, headers, **over) -> dict:
    r = await client.post(
        "/api/questions", json=question_payload(**over), headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()


async def make_answer(
    client, question, headers, body="Start with the loop invariant."
) -> dict:
    r = await client.post(
        f"/api/questions/{question['id']}/answers", json={"body": body}, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()


async def set_reputation(user, n: int) -> None:
    from sqlalchemy import update

    async with SessionLocal() as db:
        await db.execute(update(User).where(User.id == user.id).values(reputation=n))
        await db.commit()


async def reputation_of(user) -> tuple[int, int]:
    """(users.reputation, sum of the ledger): they must always agree."""
    from sqlalchemy import func, select

    from app.models.qa import ReputationEvent

    async with SessionLocal() as db:
        total = await db.scalar(select(User.reputation).where(User.id == user.id))
        ledger = await db.scalar(
            select(func.coalesce(func.sum(ReputationEvent.points), 0)).where(
                ReputationEvent.user_id == user.id
            )
        )
    return total, ledger
