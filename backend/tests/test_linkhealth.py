import httpx
from sqlalchemy import select, update

from app.db.session import SessionLocal
from app.models.content import ResourceLink
from app.services import linkhealth
from tests.factories import make_resource, make_user


def client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def no_ssrf(
    url,
):  # DNS is not under test here (tests/test_ssrf.py covers the guard)
    return None


async def link_of(resource) -> ResourceLink:
    async with SessionLocal() as db:
        return (
            await db.execute(
                select(ResourceLink).where(
                    ResourceLink.id
                    == __import__("uuid").UUID(resource["links"][0]["id"])
                )
            )
        ).scalar_one()


async def run(url_status: dict[str, int], monkeypatch, **kw):
    monkeypatch.setattr(linkhealth, "assert_public_url", no_ssrf)
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append((req.method, str(req.url)))
        return httpx.Response(url_status.get(str(req.url), 200))

    async with SessionLocal() as db:
        n = await linkhealth.check_links(db, client_for(handler), **kw)
    return n, seen


async def only_this(resource):
    """Mark every other link as freshly checked so a run touches just ours."""
    async with SessionLocal() as db:
        await db.execute(
            update(ResourceLink)
            .where(
                ResourceLink.id != __import__("uuid").UUID(resource["links"][0]["id"])
            )
            .values(checked_at=__import__("sqlalchemy").func.now())
        )
        await db.commit()


async def test_dead_after_two_failed_checks_and_recovers(client, monkeypatch):
    _, h = await make_user("verified_ufazian")
    res = await make_resource(client, h)
    url = res["links"][0]["url"]
    await only_this(res)
    await run({url: 404}, monkeypatch)
    first = await link_of(res)
    assert (first.fail_count, first.is_dead, first.health) == (1, False, "ok")
    # not due again for a day, so a second run skips it
    n, _ = await run({url: 404}, monkeypatch)
    assert n == 0
    async with SessionLocal() as db:
        await db.execute(
            update(ResourceLink)
            .where(ResourceLink.id == first.id)
            .values(checked_at=None)
        )
        await db.commit()
    await run({url: 410}, monkeypatch)
    dead = await link_of(res)
    assert dead.is_dead and dead.health == "dead"
    shown = (await client.get(f"/api/resources/{res['call_number']}")).json()
    assert shown["links"][0]["health"] == "dead"
    async with SessionLocal() as db:
        await db.execute(
            update(ResourceLink)
            .where(ResourceLink.id == first.id)
            .values(checked_at=None)
        )
        await db.commit()
    await run({}, monkeypatch)  # back to 200
    back = await link_of(res)
    assert (back.fail_count, back.is_dead, back.health) == (0, False, "ok")


async def test_reported_link_dies_on_one_failure_and_a_pass_clears_the_report(
    client, monkeypatch
):
    _, h = await make_user("verified_ufazian")
    _, reader = await make_user("user")
    bad, good = await make_resource(client, h), await make_resource(client, h)
    for res in (bad, good):
        r = await client.put(
            f"/api/links/{res['links'][0]['id']}/broken", headers=reader
        )
        assert r.status_code == 200 and r.json()["health"] == "reported"
    again = await client.put(
        f"/api/links/{bad['links'][0]['id']}/broken", headers=reader
    )
    assert again.json()["health"] == "reported"  # idempotent
    shown = (await client.get(f"/api/resources/{bad['call_number']}")).json()
    assert shown["links"][0]["health"] == "reported"

    await only_this(bad)
    async with SessionLocal() as db:
        await db.execute(
            update(ResourceLink)
            .where(ResourceLink.id == __import__("uuid").UUID(good["links"][0]["id"]))
            .values(checked_at=None)
        )
        await db.commit()
    await run({bad["links"][0]["url"]: 503}, monkeypatch)
    assert (await link_of(bad)).health == "dead"
    assert (await link_of(good)).health == "ok"  # check passed: report cleared


async def test_report_broken_needs_sign_in_and_a_published_link(client):
    _, h = await make_user("verified_ufazian")
    _, adm = await make_user("admin")
    res = await make_resource(client, h)
    lid = res["links"][0]["id"]
    assert (await client.put(f"/api/links/{lid}/broken")).status_code == 401
    import uuid

    assert (
        await client.put(f"/api/links/{uuid.uuid4()}/broken", headers=h)
    ).status_code == 404
    await client.post(
        f"/api/content/{res['id']}/hide", json={"reason": "gone"}, headers=adm
    )
    assert (await client.put(f"/api/links/{lid}/broken", headers=h)).status_code == 404


async def test_is_alive_rules(monkeypatch):
    monkeypatch.setattr(linkhealth, "assert_public_url", no_ssrf)

    def make(status_head, status_get=200, redirect=False):
        def handler(req):
            if redirect:
                return httpx.Response(302, headers={"location": "/next"})
            return httpx.Response(status_head if req.method == "HEAD" else status_get)

        return client_for(handler)

    u = "https://example.org/x"
    assert await linkhealth.is_alive(u, make(200))
    assert await linkhealth.is_alive(u, make(405, 200))  # HEAD refused, GET fine
    assert await linkhealth.is_alive(u, make(403))  # bot wall: cannot tell
    assert not await linkhealth.is_alive(u, make(404, 404))
    assert not await linkhealth.is_alive(u, make(500))
    assert not await linkhealth.is_alive(u, make(200, redirect=True))  # redirect loop

    def boom(req):
        raise httpx.ConnectError("down")

    assert not await linkhealth.is_alive(u, client_for(boom))

    async def blocked(url):
        raise linkhealth.BlockedUrl("private")

    monkeypatch.setattr(linkhealth, "assert_public_url", blocked)
    assert not await linkhealth.is_alive(u, make(200))
