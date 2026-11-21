from app.core.config import settings
from app.services import reputation
from tests.factories import (
    make_answer,
    make_question,
    make_resource,
    make_user,
    reputation_of,
    set_reputation,
)


async def vote(client, item, headers, value=1):
    return await client.put(
        f"/api/content/{item['id']}/vote", json={"value": value}, headers=headers
    )


async def test_upvotes_follow_the_points_table_and_ledger_stays_in_sync(client):
    asker, ah = await make_user("verified_ufazian")
    answerer, bh = await make_user("verified_ufazian")
    _, voter = await make_user("user")
    q = await make_question(client, ah)
    a = await make_answer(client, q, bh)
    await vote(client, q, voter)
    await vote(client, a, voter)
    assert await reputation_of(asker) == (reputation.UPVOTE_POINTS["question"],) * 2
    assert await reputation_of(answerer) == (reputation.UPVOTE_POINTS["answer"],) * 2


async def test_vote_events_are_idempotent_flip_and_undo(client):
    author, h = await make_user("verified_ufazian")
    _, voter = await make_user("verified_ufazian")
    res = await make_resource(client, h)
    up = reputation.UPVOTE_POINTS["resource"]
    await vote(client, res, voter, 1)
    await vote(client, res, voter, 1)  # repeating changes nothing
    assert await reputation_of(author) == (up, up)
    await vote(client, res, voter, -1)  # flipping rewrites the same ledger row
    assert await reputation_of(author) == (reputation.DOWNVOTE_POINTS,) * 2
    await vote(client, res, voter, 0)
    assert await reputation_of(author) == (0, 0)
    rows = (await client.get("/api/me/reputation", headers=h)).json()["items"]
    assert rows == []


async def test_self_votes_earn_nothing(client):
    author, h = await make_user("verified_ufazian")
    q = await make_question(client, h)
    r = await vote(client, q, h)
    assert r.status_code == 403 and r.json()["code"] == "self_vote"
    assert await reputation_of(author) == (0, 0)


async def test_downvoting_answers_is_a_privilege(client):
    _, ah = await make_user("verified_ufazian")
    _, bh = await make_user("verified_ufazian")
    low, low_h = await make_user("user")
    _, admin = await make_user("admin")
    q = await make_question(client, ah)
    a = await make_answer(client, q, bh)
    r = await vote(client, a, low_h, -1)
    assert r.status_code == 403 and r.json()["code"] == "privilege_required"
    await vote(client, a, low_h, 1)  # upvoting is free
    await set_reputation(low, reputation.PRIVILEGES["downvote_answers"][0])
    assert (await vote(client, a, low_h, -1)).status_code == 200
    assert (
        await vote(client, a, admin, -1)
    ).status_code == 200  # admins skip thresholds
    res = await make_resource(client, ah)
    _, fresh = await make_user("user")
    assert (
        await vote(client, res, fresh, -1)
    ).status_code == 200  # other types unchanged


async def test_daily_cap_limits_vote_reputation(client, monkeypatch):
    monkeypatch.setattr(settings, "REP_DAILY_CAP", 12)
    author, h = await make_user("verified_ufazian")
    q = await make_question(client, h)
    answers = [
        await make_answer(client, q, h, f"Answer number {i} is here.") for i in range(3)
    ]
    _, v1 = await make_user("verified_ufazian")
    _, v2 = await make_user("verified_ufazian")
    _, v3 = await make_user("verified_ufazian")
    # 10 + 2 (clipped) + 0: the cap is 12 per rolling day
    for a, v in zip(answers, (v1, v2, v3)):
        assert (await vote(client, a, v)).status_code == 200
    # the author answered their own question, voters are others: reputation capped at 12
    assert await reputation_of(author) == (12, 12)
    await vote(
        client, answers[0], v1, 0
    )  # freeing the first 10 lets the clipped ones stay clipped
    assert (await reputation_of(author))[0] == (await reputation_of(author))[1]


async def test_acceptance_points_and_no_reward_for_self_accept(client):
    asker, ah = await make_user("verified_ufazian")
    answerer, bh = await make_user("verified_ufazian")
    q = await make_question(client, ah)
    mine = await make_answer(client, q, ah, "I found the answer myself!")
    theirs = await make_answer(client, q, bh)
    await client.put(f"/api/answers/{mine['id']}/accept", headers=ah)
    assert await reputation_of(asker) == (0, 0)
    await client.put(f"/api/answers/{theirs['id']}/accept", headers=ah)
    assert await reputation_of(answerer) == (reputation.ANSWER_ACCEPTED_POINTS,) * 2
    assert await reputation_of(asker) == (reputation.ACCEPTED_ANSWER_POINTS,) * 2
    await client.put(
        f"/api/answers/{theirs['id']}/accept", headers=ah
    )  # repeat: no double award
    assert await reputation_of(answerer) == (reputation.ANSWER_ACCEPTED_POINTS,) * 2
    await client.delete(f"/api/answers/{theirs['id']}/accept", headers=ah)
    assert await reputation_of(answerer) == (0, 0) and await reputation_of(asker) == (
        0,
        0,
    )


async def test_rules_page_is_public_and_matches_the_code(client):
    r = await client.get("/api/reputation/rules")
    assert r.status_code == 200
    body = r.json()
    pts = {p["reason"]: p["points"] for p in body["points"]}
    assert pts["upvote_answer"] == reputation.UPVOTE_POINTS["answer"]
    assert pts["downvote"] == reputation.DOWNVOTE_POINTS
    assert {p["key"]: p["threshold"] for p in body["privileges"]} == {
        k: v[0] for k, v in reputation.PRIVILEGES.items()
    }
    assert body["daily_vote_cap"] == settings.REP_DAILY_CAP


async def test_history_is_cursor_paged_and_private(client):
    author, h = await make_user("verified_ufazian")
    voters = [await make_user("verified_ufazian") for _ in range(3)]
    res = [await make_resource(client, h) for _ in range(3)]
    for r, (_, v) in zip(res, voters):
        await vote(client, r, v)
    assert (await client.get("/api/me/reputation")).status_code == 401
    page = (await client.get("/api/me/reputation?limit=2", headers=h)).json()
    assert len(page["items"]) == 2 and page["next_cursor"]
    rest = (
        await client.get(
            f"/api/me/reputation?limit=2&cursor={page['next_cursor']}", headers=h
        )
    ).json()
    assert len(rest["items"]) == 1 and rest["next_cursor"] is None
    assert page["items"][0]["reason"] == "vote_up" and page["items"][0][
        "call_number"
    ].startswith("RES-")
    assert (
        await client.get("/api/me/reputation?cursor=bad", headers=h)
    ).status_code == 400
    me = (await client.get("/api/auth/me", headers=h)).json()
    assert me["reputation"] == 3 * reputation.UPVOTE_POINTS["resource"]
