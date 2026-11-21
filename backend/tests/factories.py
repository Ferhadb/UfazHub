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
