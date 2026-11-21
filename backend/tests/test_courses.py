import uuid

from tests.factories import make_article, make_resource, make_user


async def admin_setup(client):
    admin, ah = await make_user("admin")
    tag = uuid.uuid4().hex[:6]
    r = await client.post(
        "/api/programs",
        json={"slug": f"cs-{tag}", "name": "Computer Science", "description": "x"},
        headers=ah,
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        "/api/courses",
        json={
            "program_slug": f"cs-{tag}",
            "slug": f"algorithms-l2-{tag}",
            "name": "Algorithms",
            "level": "L2",
        },
        headers=ah,
    )
    assert r.status_code == 201, r.text
    return ah, f"cs-{tag}", f"algorithms-l2-{tag}"


async def test_programs_list_courses_and_slugs_are_unique(client):
    ah, program, course = await admin_setup(client)
    progs = (await client.get("/api/programs")).json()
    mine = next(p for p in progs if p["slug"] == program)
    assert [(c["slug"], c["level"]) for c in mine["courses"]] == [(course, "L2")]
    dup = await client.post(
        "/api/programs", json={"slug": program, "name": "Again"}, headers=ah
    )
    assert dup.status_code == 409 and dup.json()["code"] == "slug_taken"
    bad = await client.post(
        "/api/courses",
        json={"program_slug": "nope", "slug": "z", "name": "Zed", "level": "L1"},
        headers=ah,
    )
    assert bad.status_code == 400 and "program_slug" in bad.json()["fields"]
    bad_level = await client.post(
        "/api/courses",
        json={"program_slug": program, "slug": "q", "name": "Qq", "level": "L9"},
        headers=ah,
    )
    assert bad_level.status_code == 422


async def test_only_admins_create_programs_courses_and_paths(client):
    _, uh = await make_user("verified_ufazian")
    for method, url, body in [
        ("post", "/api/programs", {"slug": "a-b", "name": "AB"}),
        (
            "post",
            "/api/courses",
            {"program_slug": "a", "slug": "b", "name": "Bb", "level": "L1"},
        ),
        ("put", "/api/courses/x/path", {"item_ids": []}),
    ]:
        assert (await client.request(method, url, json=body)).status_code == 401
        r = await client.request(method, url, json=body, headers=uh)
        assert r.status_code == 403, url


async def test_authors_attach_content_and_course_lists_it(client):
    ah, _, course = await admin_setup(client)
    _, h = await make_user("verified_ufazian")
    _, other = await make_user("verified_ufazian")
    res = await make_resource(client, h, title="Sorting notes")
    art = await make_article(client, h)
    r = await client.put(
        f"/api/content/{res['id']}/courses", json={"course_slugs": [course]}, headers=h
    )
    assert r.status_code == 200 and r.json()[0]["name"] == "Algorithms"
    await client.put(
        f"/api/content/{art['id']}/courses", json={"course_slugs": [course]}, headers=h
    )
    # someone else's content, unknown courses, guests
    assert (
        await client.put(
            f"/api/content/{res['id']}/courses",
            json={"course_slugs": [course]},
            headers=other,
        )
    ).status_code == 403
    unknown = await client.put(
        f"/api/content/{res['id']}/courses", json={"course_slugs": ["nope"]}, headers=h
    )
    assert unknown.status_code == 400
    assert (
        await client.put(f"/api/content/{res['id']}/courses", json={"course_slugs": []})
    ).status_code == 401

    detail = (await client.get(f"/api/courses/{course}")).json()
    assert detail["item_count"] == 2 and detail["start_here"] == []
    only = (await client.get(f"/api/courses/{course}/items?type=article")).json()
    assert [i["id"] for i in only["items"]] == [art["id"]]
    assert (await client.get("/api/courses/missing")).status_code == 404
    got = (await client.get(f"/api/content/{res['id']}/courses")).json()
    assert [c["slug"] for c in got] == [course]

    # detaching clears the course
    await client.put(
        f"/api/content/{res['id']}/courses", json={"course_slugs": []}, headers=h
    )
    assert (await client.get(f"/api/courses/{course}")).json()["item_count"] == 1


async def test_start_here_path_is_ordered_replaceable_and_validated(client):
    ah, _, course = await admin_setup(client)
    _, h = await make_user("verified_ufazian")
    a = await make_resource(client, h, title="First read")
    b = await make_resource(client, h, title="Second read")
    c = await make_article(client, h)
    r = await client.put(
        f"/api/courses/{course}/path", json={"item_ids": [b["id"], a["id"]]}, headers=ah
    )
    assert r.status_code == 200, r.text
    assert [i["id"] for i in r.json()["start_here"]] == [b["id"], a["id"]]
    assert r.json()["item_count"] == 2  # listing a path item attaches it

    r = await client.put(
        f"/api/courses/{course}/path", json={"item_ids": [a["id"], c["id"]]}, headers=ah
    )
    assert [i["id"] for i in r.json()["start_here"]] == [a["id"], c["id"]]
    items = (await client.get(f"/api/courses/{course}/items")).json()["items"]
    assert {i["id"] for i in items} == {
        a["id"],
        b["id"],
        c["id"],
    }  # b stays, off the path

    for bad, code in (([str(uuid.uuid4())], 400), ([a["id"]] * 21, 422)):
        r = await client.put(
            f"/api/courses/{course}/path", json={"item_ids": bad}, headers=ah
        )
        assert r.status_code == code
    audit = (await client.get("/api/admin/audit?action=course.path", headers=ah)).json()
    assert audit["items"]


async def test_hidden_items_drop_off_the_course(client):
    ah, _, course = await admin_setup(client)
    _, h = await make_user("verified_ufazian")
    res = await make_resource(client, h)
    await client.put(
        f"/api/courses/{course}/path", json={"item_ids": [res["id"]]}, headers=ah
    )
    await client.post(
        f"/api/content/{res['id']}/hide", json={"reason": "outdated"}, headers=ah
    )
    detail = (await client.get(f"/api/courses/{course}")).json()
    assert detail["item_count"] == 0 and detail["start_here"] == []
