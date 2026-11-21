import uuid

from tests.factories import (
    make_answer,
    make_question,
    make_resource,
    make_user,
    set_reputation,
)


def unique() -> str:
    return "Zq" + uuid.uuid4().hex[:8]


async def test_profile_patch_validates_and_public_profile_hides_email(client):
    name = unique()
    user, h = await make_user("verified_ufazian", name=name)
    r = await client.patch(
        "/api/me/profile",
        json={
            "bio": "Third-year in geology.",
            "faculty": "Geological Engineering",
            "graduation_year": 2027,
            "job_title": "Intern at SOCAR",
            "socials": {"github": "https://github.com/someone", "x": ""},
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["socials"] == {"github": "https://github.com/someone"}
    pub = (await client.get(f"/api/people/{user.id}")).json()
    assert pub["faculty"] == "Geological Engineering" and pub["job_title"].startswith(
        "Intern"
    )
    assert "email" not in pub
    for bad in (
        {"socials": {"github": "javascript:alert(1)"}},
        {"socials": {"myspace": "https://example.org"}},
        {"graduation_year": 1850},
        {"bio": "x" * 501},
    ):
        assert (
            await client.patch("/api/me/profile", json=bad, headers=h)
        ).status_code == 422, bad
    blank = await client.patch(
        "/api/me/profile", json={"display_name": "  "}, headers=h
    )
    assert blank.status_code == 400 and "display_name" in blank.json()["fields"]
    # untouched fields survive a partial patch; a name change shows up
    await client.patch("/api/me/profile", json={"display_name": name + "x"}, headers=h)
    again = (await client.get(f"/api/people/{user.id}")).json()
    assert (
        again["bio"] == "Third-year in geology." and again["display_name"] == name + "x"
    )
    assert (await client.patch("/api/me/profile", json={"bio": "x"})).status_code == 401
    _, muted = await make_user(status="muted")
    assert (
        await client.patch("/api/me/profile", json={"bio": "x"}, headers=muted)
    ).status_code == 403


async def test_directory_search_filters_and_hides_banned_and_unverified(client):
    tag = unique()
    a, ah = await make_user("verified_ufazian", name=f"{tag} Alpha")
    b, bh = await make_user("user", name=f"{tag} Beta")
    await make_user("user", name=f"{tag} Gamma", status="banned")
    await make_user("user", name=f"{tag} Delta", verified=False)
    await client.patch(
        "/api/me/profile", json={"faculty": "CS", "graduation_year": 2026}, headers=ah
    )
    await set_reputation(a, 50)
    got = (await client.get("/api/people", params={"q": tag})).json()["items"]
    assert [p["display_name"] for p in got] == [f"{tag} Alpha", f"{tag} Beta"]
    only = (await client.get("/api/people", params={"q": tag, "faculty": "CS"})).json()[
        "items"
    ]
    assert [p["id"] for p in only] == [str(a.id)]
    year = (
        await client.get("/api/people", params={"q": tag, "graduation_year": 2026})
    ).json()["items"]
    assert [p["id"] for p in year] == [str(a.id)]
    # LIKE wildcards are literal
    assert (await client.get("/api/people", params={"q": "%"})).json()["items"] == []
    page1 = (await client.get("/api/people", params={"q": tag, "limit": 1})).json()
    assert page1["next_cursor"]
    page2 = (
        await client.get(
            "/api/people", params={"q": tag, "limit": 1, "cursor": page1["next_cursor"]}
        )
    ).json()
    assert page2["items"][0]["id"] == str(b.id) and page2["next_cursor"] is None
    assert (
        await client.get("/api/people", params={"cursor": "garbage"})
    ).status_code == 400


async def test_banned_and_unverified_profiles_404_but_owner_and_admin_see_them(client):
    banned, _ = await make_user("user", status="banned")
    fresh, fh = await make_user("user", verified=False)
    _, adm = await make_user("admin")
    assert (await client.get(f"/api/people/{banned.id}")).status_code == 404
    assert (await client.get(f"/api/people/{fresh.id}")).status_code == 404
    assert (await client.get(f"/api/people/{fresh.id}", headers=fh)).status_code == 200
    assert (await client.get(f"/api/people/{fresh.id}", headers=adm)).status_code == 200
    assert (await client.get(f"/api/people/{uuid.uuid4()}")).status_code == 404


async def test_badges_counts_and_heatmap_come_from_real_activity(client):
    user, h = await make_user("verified_ufazian")
    _, other = await make_user("verified_ufazian")
    empty = (await client.get(f"/api/people/{user.id}")).json()
    assert [b["slug"] for b in empty["badges"]] == ["verified"]
    assert empty["activity"] == []

    await make_resource(client, h, is_research=True)
    q = await make_question(client, other)
    ans = await make_answer(client, q, h)
    assert (
        await client.put(f"/api/answers/{ans['id']}/accept", headers=other)
    ).status_code == 200
    await client.post(
        f"/api/content/{ans['id']}/comments", json={"body": "hi"}, headers=h
    )
    await set_reputation(user, 120)
    p = (await client.get(f"/api/people/{user.id}")).json()
    assert p["counts"]["resource"] == 1 and p["counts"]["answer"] == 1
    assert p["counts"]["research"] == 1 and p["counts"]["accepted_answers"] == 1
    assert {b["slug"] for b in p["badges"]} == {
        "verified",
        "first-find",
        "scholar",
        "checked",
        "regular",
    }
    assert len(p["activity"]) == 1 and p["activity"][0]["count"] >= 2


async def test_contributions_list_published_non_answer_items(client):
    user, h = await make_user("verified_ufazian")
    _, other = await make_user("verified_ufazian")
    r = await make_resource(client, h)
    q = await make_question(client, other)
    await make_answer(client, q, h)
    got = (await client.get(f"/api/people/{user.id}/contributions")).json()
    assert [i["id"] for i in got["items"]] == [r["id"]]  # the answer is not a card


async def test_avatar_upload_then_remove(client):
    from tests.factories import png_bytes

    user, h = await make_user("verified_ufazian")
    up = await client.post(
        "/api/uploads",
        files={"file": ("me.png", png_bytes(), "image/png")},
        data={"purpose": "avatar"},
        headers=h,
    )
    assert up.status_code == 201
    assert (await client.get(f"/api/people/{user.id}")).json()["avatar_url"]
    assert (await client.delete("/api/me/avatar", headers=h)).status_code == 204
    assert (await client.get(f"/api/people/{user.id}")).json()["avatar_url"] is None


async def test_leaderboard_all_time_and_month_and_contributor(client):
    star, sh = await make_user("verified_ufazian", name=unique())
    fan, fh = await make_user("verified_ufazian")
    banned, bh = await make_user("verified_ufazian", status="banned")
    res = await make_resource(client, sh)
    assert (
        await client.put(
            f"/api/content/{res['id']}/vote", json={"value": 1}, headers=fh
        )
    ).status_code == 200
    month = (await client.get("/api/leaderboard?period=month&limit=50")).json()
    row = next(r for r in month if r["person"]["id"] == str(star.id))
    assert row["points"] > 0 and row["rank"] >= 1
    assert [r["rank"] for r in month] == list(range(1, len(month) + 1))
    assert str(fan.id) not in {r["person"]["id"] for r in month}  # earned nothing
    allt = (await client.get("/api/leaderboard?period=all&limit=50")).json()
    assert str(star.id) in {r["person"]["id"] for r in allt}
    assert allt == sorted(allt, key=lambda r: -r["points"])
    top = (await client.get("/api/leaderboard/contributor-of-the-month")).json()
    assert top is None or top["rank"] == 1
    assert (await client.get("/api/leaderboard?period=year")).status_code == 422
    await set_reputation(banned, 10_000)
    allt = (await client.get("/api/leaderboard?period=all&limit=50")).json()
    assert str(banned.id) not in {r["person"]["id"] for r in allt}
