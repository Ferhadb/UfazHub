from app.core.mail import outbox
from app.db.session import SessionLocal
from app.services import notifications
from tests.factories import make_answer, make_question, make_resource, make_user


async def inbox(client, h, **params):
    r = await client.get("/api/notifications", params=params, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["items"]


async def unread(client, h):
    return (await client.get("/api/notifications/unread", headers=h)).json()["unread"]


async def test_requires_sign_in(client):
    for method, url in (
        ("get", "/api/notifications"),
        ("get", "/api/notifications/unread"),
        ("post", "/api/notifications/read"),
        ("put", "/api/notifications/settings"),
    ):
        assert (await getattr(client, method)(url)).status_code == 401


async def test_new_answer_notifies_the_asker_not_the_answerer(client):
    _, ah = await make_user("verified_ufazian")
    _, bh = await make_user("verified_ufazian")
    q = await make_question(client, ah)
    await make_answer(client, q, bh, "An answer from somebody else.")
    await make_answer(client, q, ah, "The asker answers their own question.")
    got = await inbox(client, ah)
    assert [(n["kind"], n["call_number"], n["read"]) for n in got] == [
        ("answer", q["call_number"], False)
    ]
    assert got[0]["actor"]["display_name"] and got[0]["title"] == q["title"]
    assert await inbox(client, bh) == []


async def test_comments_notify_item_author_and_parent_author_once(client):
    _, author = await make_user("verified_ufazian")
    _, a = await make_user("verified_ufazian")
    _, b = await make_user("verified_ufazian")
    res = await make_resource(client, author)

    async def comment(h, body, parent=None):
        r = await client.post(
            f"/api/content/{res['id']}/comments",
            json={"body": body, "parent_id": parent},
            headers=h,
        )
        assert r.status_code == 201, r.text
        return r.json()

    top = await comment(a, "Great find, thanks!")
    await comment(b, "I agree with A.", top["id"])
    await comment(author, "Glad it helps.")  # own thread: nobody is told about yourself
    assert [n["kind"] for n in await inbox(client, author)] == ["reply", "reply"]
    assert [n["kind"] for n in await inbox(client, a)] == ["reply"]  # B replied to A
    assert await inbox(client, b) == []


async def test_comment_on_an_answer_points_at_the_question(client):
    _, ah = await make_user("verified_ufazian")
    _, bh = await make_user("verified_ufazian")
    q = await make_question(client, ah)
    a = await make_answer(client, q, bh)
    await client.post(
        f"/api/content/{a['id']}/comments",
        json={"body": "Why does this hold?"},
        headers=ah,
    )
    n = (await inbox(client, bh))[0]
    assert n["kind"] == "reply" and n["call_number"] == q["call_number"]


async def test_accepted_answer_notifies_the_answerer_once(client):
    _, ah = await make_user("verified_ufazian")
    _, bh = await make_user("verified_ufazian")
    q = await make_question(client, ah)
    a = await make_answer(client, q, bh)
    for _ in range(2):
        await client.put(f"/api/answers/{a['id']}/accept", headers=ah)
    await client.delete(f"/api/answers/{a['id']}/accept", headers=ah)
    await client.put(f"/api/answers/{a['id']}/accept", headers=ah)
    assert [n["kind"] for n in await inbox(client, bh)] == ["answer_accepted"]


async def test_vote_milestones_fire_once_per_threshold(client, monkeypatch):
    monkeypatch.setattr(notifications, "MILESTONES", (2, 3))
    _, h = await make_user("verified_ufazian")
    voters = [await make_user("verified_ufazian") for _ in range(3)]
    res = await make_resource(client, h)
    v = lambda who, val: client.put(  # noqa: E731
        f"/api/content/{res['id']}/vote", json={"value": val}, headers=who[1]
    )
    await v(voters[0], 1)
    assert await inbox(client, h) == []
    await v(voters[1], 1)
    await v(voters[1], 0)  # drop below and cross again: still one notification
    await v(voters[1], 1)
    await v(voters[2], 1)
    got = await inbox(client, h)
    assert sorted(n["message"] for n in got) == ["2 votes", "3 votes"]
    assert {n["kind"] for n in got} == {"vote_milestone"}


async def test_moderation_actions_notify_the_author(client):
    _, h = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    res = await make_resource(client, h)
    await client.post(
        f"/api/content/{res['id']}/hide", json={"reason": "Broken link"}, headers=admin
    )
    await client.post(f"/api/content/{res['id']}/publish", headers=admin)
    got = await inbox(client, h)
    assert [n["kind"] for n in got] == ["moderation", "moderation"]
    assert {n["message"] for n in got} == {"Broken link", "approved and visible again"}
    # pinning and duplicate marks are moderation too
    _, bh = await make_user("verified_ufazian")
    q = await make_question(client, bh)
    a = await make_answer(client, q, h, "An answer that gets pinned.")
    await client.put(f"/api/answers/{a['id']}/pin", headers=admin)
    assert (await inbox(client, h))[0]["message"] == "your answer was pinned"
    q2 = await make_question(client, bh, title="A twin of the earlier question")
    await client.put(
        f"/api/questions/{q2['id']}/duplicate",
        json={"of": q["call_number"]},
        headers=admin,
    )
    assert (await inbox(client, bh))[0]["message"] == "marked as a duplicate"


async def test_cursor_unread_filter_and_mark_read(client):
    _, h = await make_user("verified_ufazian")
    _, other = await make_user("verified_ufazian")
    _, c = await make_user("verified_ufazian")
    qs = [
        await make_question(client, h, title=f"Question number {i} about topics")
        for i in range(3)
    ]
    for q in qs:
        await make_answer(client, q, c, "Here is an answer for you.")
    await make_answer(
        client, await make_question(client, other, title="Not for the first user"), c
    )
    assert await unread(client, h) == 3
    page = (await client.get("/api/notifications?limit=2", headers=h)).json()
    assert len(page["items"]) == 2 and page["next_cursor"]
    rest = (
        await client.get(
            f"/api/notifications?limit=2&cursor={page['next_cursor']}", headers=h
        )
    ).json()
    assert len(rest["items"]) == 1 and rest["next_cursor"] is None
    assert (
        await client.get("/api/notifications?cursor=junk", headers=h)
    ).status_code == 400
    first = page["items"][0]["id"]
    # someone else's id is ignored; mine is marked
    r = await client.post(
        "/api/notifications/read", json={"ids": [first]}, headers=other
    )
    assert r.json() == {"unread": 1}
    r = await client.post("/api/notifications/read", json={"ids": [first]}, headers=h)
    assert r.json() == {"unread": 2}
    assert len(await inbox(client, h, unread="true")) == 2
    r = await client.post("/api/notifications/read", json={}, headers=h)  # everything
    assert r.json() == {"unread": 0}
    assert len(await inbox(client, h)) == 3 and await unread(client, other) == 1


async def test_email_digest_only_for_opted_in_users_and_only_once(client):
    _, ah = await make_user("verified_ufazian")
    _, quiet = await make_user("verified_ufazian")
    _, bh = await make_user("verified_ufazian")
    r = await client.put(
        "/api/notifications/settings", json={"email_digest": True}, headers=ah
    )
    assert r.json() == {"email_digest": True}
    assert (await client.get("/api/notifications/settings", headers=ah)).json()[
        "email_digest"
    ] is True
    for h in (ah, quiet):
        await make_answer(
            client, await make_question(client, h), bh, "An answer to digest."
        )
    outbox.clear()
    async with SessionLocal() as db:
        assert await notifications.send_digests(db) == 1
    assert len(outbox) == 1 and "New answer on QST-" in outbox[0]["body"]
    async with SessionLocal() as db:
        assert await notifications.send_digests(db) == 0  # already emailed
    # read notifications are not emailed
    await make_answer(
        client, await make_question(client, ah, title="A second question to read"), bh
    )
    await client.post("/api/notifications/read", json={}, headers=ah)
    outbox.clear()
    async with SessionLocal() as db:
        assert await notifications.send_digests(db) == 0
    assert outbox == []
