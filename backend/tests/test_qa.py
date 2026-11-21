import pytest

from tests.factories import (
    make_answer,
    make_question,
    make_resource,
    make_user,
    set_reputation,
)


async def accept(client, answer, headers):
    return await client.put(f"/api/answers/{answer['id']}/accept", headers=headers)


async def answers(client, question, headers=None):
    r = await client.get(
        f"/api/questions/{question['call_number']}/answers", headers=headers
    )
    assert r.status_code == 200
    return r.json()["items"]


async def test_ask_with_topic_and_linked_resource(client):
    _, h = await make_user("verified_ufazian")
    res = await make_resource(client, h)
    q = await make_question(client, h, linked_resource=res["call_number"].lower())
    assert q["call_number"].startswith("QST-") and q["topic"] == "Algorithms"
    assert q["linked_resource"] == {
        "call_number": res["call_number"],
        "title": res["title"],
    }
    got = (await client.get(f"/api/questions/{q['call_number']}")).json()
    assert got["answer_count"] == 0 and got["has_accepted"] is False


async def test_linked_resource_must_exist(client):
    _, h = await make_user("verified_ufazian")
    r = await client.post(
        "/api/questions",
        json={
            "title": "A perfectly fine question title",
            "body": "With a decent body of text.",
            "topic": "Math",
            "linked_resource": "RES-9999",
        },
        headers=h,
    )
    assert r.status_code == 400 and "linked_resource" in r.json()["fields"]


@pytest.mark.parametrize(
    "actor,status",
    [
        (None, 401),
        (("user", "active", False), 403),
        (("user", "muted", True), 403),
        (("user", "banned", True), 403),
        (("user", "active", True), 201),
        (("admin", "active", True), 201),
    ],
)
async def test_ask_and_answer_permissions(client, actor, status):
    _, owner = await make_user("verified_ufazian")
    q = await make_question(client, owner)
    h = {}
    if actor:
        _, h = await make_user(actor[0], actor[1], verified=actor[2])
    body = {
        "title": "Another good question title",
        "body": "Body of the other question.",
        "topic": "Math",
    }
    assert (
        await client.post("/api/questions", json=body, headers=h)
    ).status_code == status
    r = await client.post(
        f"/api/questions/{q['id']}/answers",
        json={"body": "A helpful answer."},
        headers=h,
    )
    assert r.status_code == status


async def test_validation(client):
    _, h = await make_user("verified_ufazian")
    r = await client.post(
        "/api/questions", json={"title": "short", "body": "x", "topic": ""}, headers=h
    )
    assert r.status_code == 422 and {"title", "body", "topic"} <= set(
        r.json()["fields"]
    )


async def test_list_filters_and_unanswered(client):
    _, h = await make_user("verified_ufazian")
    a = await make_question(
        client, h, topic="Algorithms", title="Question about graphs and trees"
    )
    b = await make_question(
        client, h, topic="Physics", title="Question about entropy in physics"
    )
    await make_answer(client, a, h)
    allq = (await client.get("/api/questions")).json()["items"]
    assert [q["call_number"] for q in allq][:2] == [b["call_number"], a["call_number"]]
    assert next(q for q in allq if q["id"] == a["id"])["answer_count"] == 1
    only_phys = (await client.get("/api/questions?topic=physics")).json()["items"]
    assert [q["id"] for q in only_phys] == [b["id"]]
    open_ = (await client.get("/api/questions?unanswered=true")).json()["items"]
    assert b["id"] in [q["id"] for q in open_] and a["id"] not in [
        q["id"] for q in open_
    ]


async def test_similar_suggestions_tolerate_typos_and_skip_duplicates(client):
    _, h = await make_user("verified_ufazian")
    q1 = await make_question(client, h, title="How does Dijkstra shortest path work?")
    q2 = await make_question(client, h, title="Dijkstra shortest path explained please")
    await make_answer(client, q1, h)
    r = await client.get(
        "/api/questions/similar", params={"title": "Dijkstra shortes path"}
    )
    assert r.status_code == 200
    hits = {x["call_number"]: x for x in r.json()}
    assert q1["call_number"] in hits and hits[q1["call_number"]]["answer_count"] == 1
    d = await client.put(
        f"/api/questions/{q2['id']}/duplicate",
        json={"of": q1["call_number"]},
        headers=h,
    )
    assert d.status_code == 204
    hits = [
        x["call_number"]
        for x in (
            await client.get(
                "/api/questions/similar", params={"title": "Dijkstra shortest path"}
            )
        ).json()
    ]
    assert q2["call_number"] not in hits and q1["call_number"] in hits
    assert (
        await client.get("/api/questions/similar", params={"title": "ab"})
    ).status_code == 422


async def test_answers_sorted_accepted_then_pinned_then_votes_with_cursor(client):
    asker, ah = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    q = await make_question(client, ah)
    users = [await make_user("verified_ufazian") for _ in range(3)]
    a1 = await make_answer(client, q, users[0][1], "First answer, plain.")
    a2 = await make_answer(client, q, users[1][1], "Second answer, will be pinned.")
    a3 = await make_answer(client, q, users[2][1], "Third answer, will be accepted.")
    assert (
        await client.put(f"/api/answers/{a2['id']}/pin", headers=admin)
    ).status_code == 200
    assert (await accept(client, a3, ah)).status_code == 200
    order = [a["id"] for a in await answers(client, q)]
    assert order == [a3["id"], a2["id"], a1["id"]]
    page = (
        await client.get(f"/api/questions/{q['call_number']}/answers?limit=2")
    ).json()
    assert [a["id"] for a in page["items"]] == [a3["id"], a2["id"]] and page[
        "next_cursor"
    ]
    rest = (
        await client.get(
            f"/api/questions/{q['call_number']}/answers?limit=2&cursor={page['next_cursor']}"
        )
    ).json()
    assert [a["id"] for a in rest["items"]] == [a1["id"]] and rest[
        "next_cursor"
    ] is None
    assert (
        await client.get(f"/api/questions/{q['call_number']}/answers?cursor=zzz")
    ).status_code == 400
    got = (await client.get(f"/api/questions/{q['call_number']}")).json()
    assert got["answer_count"] == 3 and got["has_accepted"] is True


async def test_only_the_asker_accepts(client):
    asker, ah = await make_user("verified_ufazian")
    _, other = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    q = await make_question(client, ah)
    a = await make_answer(client, q, other)
    assert (await client.put(f"/api/answers/{a['id']}/accept")).status_code == 401
    for h in (other, admin):  # not even an admin
        r = await accept(client, a, h)
        assert r.status_code == 403 and r.json()["code"] == "not_asker"
    r = await accept(client, a, ah)
    assert r.status_code == 200 and r.json()["accepted"] is True
    assert (await accept(client, a, ah)).json()["accepted"] is True  # idempotent
    r = await client.delete(f"/api/answers/{a['id']}/accept", headers=other)
    assert r.status_code == 403
    r = await client.delete(f"/api/answers/{a['id']}/accept", headers=ah)
    assert r.json()["accepted"] is False


async def test_accepting_another_answer_moves_the_tick(client):
    _, ah = await make_user("verified_ufazian")
    u1, h1 = await make_user("verified_ufazian")
    u2, h2 = await make_user("verified_ufazian")
    q = await make_question(client, ah)
    a1 = await make_answer(client, q, h1)
    a2 = await make_answer(client, q, h2)
    await accept(client, a1, ah)
    await accept(client, a2, ah)
    flags = {a["id"]: a["accepted"] for a in await answers(client, q)}
    assert flags == {a1["id"]: False, a2["id"]: True}


async def test_pin_is_admin_only_and_single(client):
    _, ah = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    _, h1 = await make_user("verified_ufazian")
    q = await make_question(client, ah)
    a1 = await make_answer(client, q, h1)
    a2 = await make_answer(client, q, h1, "Another answer by the same person.")
    for h in ({}, ah, h1):
        r = await client.put(f"/api/answers/{a1['id']}/pin", headers=h)
        assert r.status_code in (401, 403)
    await client.put(f"/api/answers/{a1['id']}/pin", headers=admin)
    await client.put(f"/api/answers/{a2['id']}/pin", headers=admin)
    pinned = {a["id"]: a["pinned"] for a in await answers(client, q)}
    assert pinned == {a1["id"]: False, a2["id"]: True}
    r = await client.delete(f"/api/answers/{a2['id']}/pin", headers=admin)
    assert r.json()["pinned"] is False


async def test_duplicate_merge_and_redirect(client):
    asker, ah = await make_user("verified_ufazian")
    _, other = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    original = await make_question(
        client, admin, title="The original question title here"
    )
    dup = await make_question(client, ah, title="A rephrased copy of that question")
    third = await make_question(client, ah, title="Yet another copy of that question")

    def mark(q, of, h):
        return client.put(
            f"/api/questions/{q['id']}/duplicate", json={"of": of}, headers=h
        )

    r = await mark(dup, original["call_number"], other)  # no reputation, not the asker
    assert r.status_code == 403 and r.json()["code"] == "privilege_required"
    assert (await mark(dup, dup["call_number"], ah)).status_code == 422  # itself
    assert (await mark(dup, "QST-9999", ah)).status_code == 422  # unknown
    assert (
        await mark(dup, original["call_number"], ah)
    ).status_code == 204  # the asker
    got = (await client.get(f"/api/questions/{dup['call_number']}")).json()
    assert got["duplicate_of"]["call_number"] == original["call_number"]
    # no chains: pointing at a duplicate is refused, and a merged question stops taking answers
    assert (await mark(third, dup["call_number"], ah)).status_code == 422
    r = await client.post(
        f"/api/questions/{dup['id']}/answers",
        json={"body": "Answer on a merged one."},
        headers=other,
    )
    assert r.status_code == 409 and r.json()["code"] == "question_merged"
    # marking the original as a duplicate of something else re-points its duplicates
    await set_reputation(asker, 100)
    final = await make_question(client, admin, title="The one true question to keep")
    assert (await mark(original, final["call_number"], admin)).status_code == 204
    got = (await client.get(f"/api/questions/{dup['call_number']}")).json()
    assert got["duplicate_of"]["call_number"] == final["call_number"]
    # privileged users can merge any question; unmarking works for the same people
    assert (await mark(third, final["call_number"], ah)).status_code == 204
    assert (
        await client.delete(f"/api/questions/{third['id']}/duplicate", headers=other)
    ).status_code == 403
    assert (
        await client.delete(f"/api/questions/{third['id']}/duplicate", headers=ah)
    ).status_code == 204
    assert (await client.get(f"/api/questions/{third['call_number']}")).json()[
        "duplicate_of"
    ] is None


async def test_reputation_privilege_unlocks_duplicate_marking(client):
    _, ah = await make_user("verified_ufazian")
    expert, eh = await make_user("verified_ufazian")
    q1 = await make_question(client, ah, title="Question one is long enough")
    q2 = await make_question(client, ah, title="Question two is long enough")
    body = {"of": q1["call_number"]}
    assert (
        await client.put(f"/api/questions/{q2['id']}/duplicate", json=body, headers=eh)
    ).status_code == 403
    await set_reputation(expert, 100)
    assert (
        await client.put(f"/api/questions/{q2['id']}/duplicate", json=body, headers=eh)
    ).status_code == 204


async def test_pending_answers_are_visible_to_their_author_only(client):
    _, ah = await make_user("verified_ufazian")
    _, newbie = await make_user(
        "user"
    )  # verified email, not a verified student: pending review
    q = await make_question(client, ah)
    a = await make_answer(client, q, newbie)
    assert a["status"] == "pending_review"
    assert [x["id"] for x in await answers(client, q)] == []
    assert [x["id"] for x in await answers(client, q, newbie)] == [a["id"]]
    r = await client.put(f"/api/answers/{a['id']}/accept", headers=ah)
    assert r.status_code == 404  # cannot accept what the public cannot see


async def test_answers_stay_out_of_search(client):
    _, h = await make_user("verified_ufazian")
    q = await make_question(client, h, title="Zanzibar consensus question here")
    await make_answer(client, q, h, "Zanzibar answer text that mentions the keyword.")
    hits = (await client.get("/api/search", params={"q": "zanzibar"})).json()["items"]
    assert [x["type"] for x in hits] == ["question"]


async def test_unknown_question_404(client):
    assert (await client.get("/api/questions/QST-9999")).status_code == 404
    assert (await client.get("/api/questions/QST-9999/answers")).status_code == 404
