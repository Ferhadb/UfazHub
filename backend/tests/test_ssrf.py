"""SSRF guard and link previews. Network is faked except for one real loopback connection."""

import asyncio

import httpx
import pytest
from sqlalchemy import select

from app.core import ssrf
from app.core.ssrf import BlockedUrl
from app.db.session import SessionLocal
from app.models.content import ResourceLink
from app.services import previews
from tests.factories import make_resource, make_user

BLOCKED = [
    "127.0.0.1",
    "127.255.255.254",
    "10.0.0.1",
    "172.16.0.1",
    "172.31.255.255",
    "192.168.1.1",
    "169.254.169.254",  # cloud metadata
    "100.64.0.1",  # carrier-grade NAT
    "0.0.0.0",
    "255.255.255.255",
    "224.0.0.1",
    "239.255.255.250",  # multicast
    "192.0.2.1",
    "198.51.100.7",  # documentation ranges
    "::1",
    "::",
    "fe80::1",
    "fe80::1%eth0",
    "fc00::1",
    "fd12:3456::1",
    "ff02::1",
    "::ffff:127.0.0.1",
    "::ffff:10.0.0.1",
    "::ffff:169.254.169.254",  # IPv4-mapped IPv6
    "64:ff9b::7f00:1",
    "64:ff9b::a9fe:a9fe",  # NAT64 wrapping loopback / metadata
    "2002:7f00:1::1",  # 6to4 wrapping loopback
]
PUBLIC = ["8.8.8.8", "93.184.216.34", "2606:4700:4700::1111", "::ffff:8.8.8.8"]


@pytest.mark.parametrize("addr", BLOCKED)
def test_non_public_addresses_are_blocked(addr):
    assert not ssrf.is_public(addr)


@pytest.mark.parametrize("addr", PUBLIC)
def test_public_addresses_pass(addr):
    assert ssrf.is_public(addr)


def fake_dns(monkeypatch, table: dict[str, list[str]]):
    async def resolve(host, port):
        if host not in table:
            raise OSError("no such host")
        return table[host]

    monkeypatch.setattr(ssrf, "_resolve", resolve)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.org/x",
        "gopher://example.org",
        "javascript:alert(1)",
        "http://example.org:22/",
        "http://example.org:6379/",
        "https://example.org:8443/",
        "http://localhost/",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://0/",
        "http://2130706433/",
        "http://0x7f.1/",
        "http://metadata.internal/",
        "http://dualstack.example.org/",
        "http:///nohost",
    ],
)
async def test_guard_rejects(monkeypatch, url):
    fake_dns(
        monkeypatch,
        {
            "example.org": ["93.184.216.34"],
            "localhost": ["127.0.0.1", "::1"],
            "metadata.internal": ["169.254.169.254"],
            "dualstack.example.org": [
                "93.184.216.34",
                "10.0.0.5",
            ],  # one bad record is enough
            "0": ["0.0.0.0"],
            "2130706433": ["127.0.0.1"],
            "0x7f.1": ["127.0.0.1"],
        },
    )
    with pytest.raises(BlockedUrl):
        await ssrf.assert_public_url(url)


async def test_guard_allows_public(monkeypatch):
    fake_dns(
        monkeypatch,
        {"example.org": ["93.184.216.34"], "v6.example.org": ["2606:4700:4700::1111"]},
    )
    for url in (
        "http://example.org/",
        "https://example.org/a?b=1",
        "https://example.org:443/",
        "https://v6.example.org/",
    ):
        await ssrf.assert_public_url(url)


async def test_unresolvable_host_is_blocked(monkeypatch):
    fake_dns(monkeypatch, {})
    with pytest.raises(BlockedUrl):
        await ssrf.assert_public_url("https://nope.example/")


def mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=False
    )


HTML = '<html><head><title> Hello\n World </title><meta property="og:image" content="/img/cover.png"><link rel="shortcut icon" href="/fav.ico"></head><body>x</body></html>'


async def test_fetch_follows_public_redirects_and_parses(monkeypatch):
    fake_dns(
        monkeypatch, {"a.example": ["93.184.216.34"], "b.example": ["93.184.216.35"]}
    )

    def handler(req: httpx.Request):
        if req.url.host == "a.example":
            return httpx.Response(301, headers={"location": "https://b.example/final"})
        return httpx.Response(
            200, headers={"content-type": "text/html; charset=utf-8"}, text=HTML
        )

    async with mock_client(handler) as c:
        final, html = await previews.fetch_html("http://a.example/start", c)
    assert final == "https://b.example/final"
    assert previews.parse_preview(html, final) == {
        "title": "Hello World",
        "image": "https://b.example/img/cover.png",
        "favicon": "https://b.example/fav.ico",
    }


@pytest.mark.parametrize(
    "target",
    [
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://internal.example/",
        "file:///etc/passwd",
        "http://[::1]:80/",
    ],
)
async def test_redirect_to_private_target_is_blocked(monkeypatch, target):
    fake_dns(
        monkeypatch, {"a.example": ["93.184.216.34"], "internal.example": ["10.1.2.3"]}
    )
    hits = []

    def handler(req: httpx.Request):
        hits.append(str(req.url))
        return httpx.Response(302, headers={"location": target})

    async with mock_client(handler) as c:
        with pytest.raises(BlockedUrl):
            await previews.fetch_html("http://a.example/", c)
    assert hits == ["http://a.example/"]  # the private target was never requested


async def test_at_most_three_redirects(monkeypatch):
    fake_dns(monkeypatch, {"a.example": ["93.184.216.34"]})
    hits = []

    def handler(req):
        hits.append(1)
        return httpx.Response(
            302, headers={"location": f"http://a.example/{len(hits)}"}
        )

    async with mock_client(handler) as c:
        with pytest.raises(BlockedUrl, match="redirects"):
            await previews.fetch_html("http://a.example/", c)
    assert len(hits) == 4  # the original request plus three redirects


async def test_non_html_is_refused_and_body_is_capped(monkeypatch):
    fake_dns(monkeypatch, {"a.example": ["93.184.216.34"]})
    async with mock_client(
        lambda r: httpx.Response(
            200, headers={"content-type": "application/pdf"}, content=b"%PDF"
        )
    ) as c:
        with pytest.raises(BlockedUrl):
            await previews.fetch_html("http://a.example/", c)
    big = b"<html><head><title>T</title></head>" + b"x" * (previews.MAX_BYTES * 3)
    async with mock_client(
        lambda r: httpx.Response(
            200, headers={"content-type": "text/html"}, content=big
        )
    ) as c:
        _, html = await previews.fetch_html("http://a.example/", c)
    assert len(html) <= previews.MAX_BYTES and "<title>T</title>" in html


async def test_guarded_client_refuses_a_real_loopback_server():
    """End to end through the real transport: connecting to 127.0.0.1 must fail at connect time."""
    served = []

    async def handle(reader, writer):
        served.append(await reader.read(100))
        writer.write(
            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Type: text/html\r\n\r\nhi"
        )
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        async with ssrf.guarded_client() as c:
            with pytest.raises((BlockedUrl, httpx.HTTPError)):
                await c.get(f"http://127.0.0.1:{port}/")
            with pytest.raises((BlockedUrl, httpx.HTTPError)):
                await c.get(f"http://localhost:{port}/")
    finally:
        server.close()
    assert served == []  # not a single byte reached the internal service


async def test_dns_rebinding_is_closed_by_connect_time_check(monkeypatch):
    """A name that resolved publicly at check time but privately at connect time is still refused."""
    answers = iter([["93.184.216.34"], ["127.0.0.1"]])

    async def resolve(host, port):
        return next(answers)

    monkeypatch.setattr(ssrf, "_resolve", resolve)
    await ssrf.assert_public_url("http://rebind.example/")  # check passes
    with pytest.raises(BlockedUrl):
        await ssrf.resolve_public(
            "rebind.example", 80
        )  # connect-time lookup now says loopback


async def test_refresh_stores_preview_and_failures_are_stamped(client, monkeypatch):
    _, h = await make_user("verified_ufazian")
    res = await make_resource(
        client,
        h,
        links=[
            {"url": "https://ok.example/page"},
            {"url": "https://internal.example/x"},
        ],
    )
    fake_dns(
        monkeypatch, {"ok.example": ["93.184.216.34"], "internal.example": ["10.0.0.9"]}
    )
    monkeypatch.setattr(
        previews,
        "guarded_client",
        lambda: mock_client(
            lambda r: httpx.Response(
                200, headers={"content-type": "text/html"}, text=HTML
            )
        ),
    )
    async with SessionLocal() as db:
        ids = (
            await db.execute(
                select(ResourceLink.id, ResourceLink.url).where(
                    ResourceLink.resource_id == res["id"]
                )
            )
        ).all()
        for link_id, url in ids:
            assert await previews.refresh_link_preview(db, link_id) is (
                "ok.example" in url
            )
    got = (await client.get(f"/api/resources/{res['call_number']}")).json()["links"]
    by_url = {link["url"]: link for link in got}
    ok, bad = by_url["https://ok.example/page"], by_url["https://internal.example/x"]
    assert (
        ok["preview_title"] == "Hello World"
        and ok["preview_image"] == "https://ok.example/img/cover.png"
    )
    assert bad["preview_title"] is None
    async with SessionLocal() as db:
        stamped = (
            (
                await db.execute(
                    select(ResourceLink.preview_fetched_at).where(
                        ResourceLink.resource_id == res["id"]
                    )
                )
            )
            .scalars()
            .all()
        )
    assert all(stamped)  # failures are stamped too, so nothing is refetched in a loop


def test_parse_ignores_non_http_assets():
    out = previews.parse_preview(
        '<title>T</title><meta property="og:image" content="javascript:alert(1)"><link rel="icon" href="data:image/png;base64,xx">',
        "https://x.example/",
    )
    assert out == {"title": "T", "image": None, "favicon": None}
