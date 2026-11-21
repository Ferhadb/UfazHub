import uuid

from tests.factories import make_resource, make_user


def uniq() -> str:
    return "".join(chr(ord("a") + int(c, 16)) for c in uuid.uuid4().hex[:10]) + "x"


async def hits(client, q, **params):
    r = await client.get("/api/search", params={"q": q, **params})
    assert r.status_code == 200, r.text
    return r.json()["items"]


async def trusted():
    return (await make_user(role="verified_ufazian"))[1]


async def test_title_match_outranks_description_and_tag_matches(client):
    h, word = await trusted(), uniq()
    in_desc = await make_resource(
        client,
        h,
        title="Unrelated handbook",
        description=f"Mentions {word} once in passing.",
        tags=["misc"],
    )
    in_tag = await make_resource(
        client,
        h,
        title="Another handbook",
        description="Nothing relevant to see here.",
        tags=[word],
    )
    in_title = await make_resource(
        client,
        h,
        title=f"All about {word}",
        description="Plain description for the card.",
        tags=["misc"],
    )
    order = [i["id"] for i in await hits(client, word)]
    assert order == [in_title["id"], in_tag["id"], in_desc["id"]]  # weights A > B > C


async def test_typo_tolerance_and_accent_folding(client):
    h, word = await trusted(), uniq()
    item = await make_resource(client, h, title=f"{word.capitalize()}ometry made easy")
    typo = word[:-2] + word[-1]  # one letter dropped
    assert item["id"] in [i["id"] for i in await hits(client, typo + "ometry")]
    # Matched through the full-text index alone: the title shares nothing with the query.
    other = uniq()
    az = await make_resource(
        client, h, title=f"Konspekt {word}", description=f"Əlgəbr {other} və həndəsə."
    )
    assert [i["id"] for i in await hits(client, f"elgebr {other}")] == [az["id"]]
    assert [i["id"] for i in await hits(client, f"əlgəbr {other}")] == [az["id"]]
    fr = await make_resource(
        client,
        h,
        title=f"Résumé de cours {word}",
        description="Révision avant l’examen.",
    )
    assert fr["id"] in [i["id"] for i in await hits(client, f"resume {word}")]


async def test_stemming_and_websearch_syntax(client):
    h, word = await trusted(), uniq()
    a = await make_resource(
        client, h, title=f"{word} algorithms", description="sorting graphs"
    )
    b = await make_resource(
        client, h, title=f"{word} databases", description="sorting joins"
    )
    assert {i["id"] for i in await hits(client, f"{word} algorithm")} >= {a["id"]}
    ids = {i["id"] for i in await hits(client, f"{word} -databases")}
    assert a["id"] in ids and b["id"] not in ids
    phrase = {i["id"] for i in await hits(client, f'"{word} databases"')}
    assert b["id"] in phrase and a["id"] not in phrase


async def test_snippets_use_markers_not_html(client):
    h, word = await trusted(), uniq()
    await make_resource(
        client,
        h,
        title=f"{word} guide",
        description=f"Read this <script>alert(1)</script> before touching {word} in the lab.",
    )
    hit = (await hits(client, word))[0]
    assert "\x02" + word in hit["title_hl"] and "\x03" in hit["title_hl"]
    assert "\x02" + word + "\x03" in hit["snippet"]
    assert "<mark" not in hit["snippet"] + hit["title_hl"]


async def test_filters(client):
    h, word = await trusted(), uniq()
    r1 = await make_resource(
        client,
        h,
        title=f"{word} one",
        difficulty="beginner",
        tags=["Exams"],
        is_research=False,
    )
    r2 = await make_resource(
        client,
        h,
        title=f"{word} two",
        difficulty="advanced",
        tags=["Papers"],
        is_research=True,
    )
    assert {i["id"] for i in await hits(client, word)} == {r1["id"], r2["id"]}
    assert [i["id"] for i in await hits(client, word, difficulty="advanced")] == [
        r2["id"]
    ]
    assert [i["id"] for i in await hits(client, word, tag="exams")] == [r1["id"]]
    assert [i["id"] for i in await hits(client, word, research=True)] == [r2["id"]]
    assert len(await hits(client, word, type="resource")) == 2
    assert await hits(client, word, type="article") == []
    assert (
        await client.get("/api/search", params={"q": word, "type": "nope"})
    ).status_code == 422
    assert (await client.get("/api/search", params={"q": "a"})).status_code == 422


async def test_cursor_pagination_is_stable(client):
    h, word = await trusted(), uniq()
    for i in range(5):
        await make_resource(client, h, title=f"{word} part {i}")
    seen, cursor = [], None
    while True:
        r = (
            await client.get(
                "/api/search",
                params={
                    "q": word,
                    "limit": 2,
                    **({"cursor": cursor} if cursor else {}),
                },
            )
        ).json()
        seen += [i["id"] for i in r["items"]]
        cursor = r["next_cursor"]
        if not cursor:
            break
    assert len(seen) == 5 == len(set(seen))
    assert (
        await client.get("/api/search", params={"q": word, "cursor": "nope"})
    ).json()["code"] == "invalid_cursor"


async def test_index_follows_edits(client):
    h, word, other = await trusted(), uniq(), uniq()
    item = await make_resource(client, h, title=f"{word} notes")
    assert await hits(client, other) == []
    await client.patch(
        f"/api/resources/{item['id']}", json={"tags": [other]}, headers=h
    )
    assert [i["id"] for i in await hits(client, other)] == [item["id"]]
    await client.patch(
        f"/api/resources/{item['id']}",
        json={"best_part": f"the {other}-ish part", "tags": ["x1"]},
        headers=h,
    )
    assert [i["id"] for i in await hits(client, other)] == [item["id"]]
    await client.patch(
        f"/api/resources/{item['id']}", json={"best_part": "gone"}, headers=h
    )
    assert await hits(client, other) == []
    await client.patch(
        f"/api/resources/{item['id']}", json={"title": f"{other} renamed"}, headers=h
    )
    assert [i["id"] for i in await hits(client, other)] == [item["id"]]
