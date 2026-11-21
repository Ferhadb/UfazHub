import io

import pytest
from PIL import Image

from app.core.signing import sign_media, verify_media
from tests.factories import make_user, png_bytes


async def upload(
    client, headers, data, name="a.png", mime="image/png", purpose="attachment"
):
    return await client.post(
        "/api/uploads",
        files={"file": (name, data, mime)},
        data={"purpose": purpose},
        headers=headers,
    )


def media_path(url: str) -> str:
    return url  # urls are API-relative (/api/media/...)


async def test_image_upload_makes_webp_variants_and_signed_urls_serve(client):
    _, h = await make_user()
    r = await upload(client, h, png_bytes((2000, 1000)))
    assert r.status_code == 201, r.text
    a = r.json()
    assert (
        a["kind"] == "image"
        and a["mime"] == "image/webp"
        and (a["width"], a["height"]) == (2000, 1000)
    )
    assert set(a["urls"]) == {"sm", "md", "lg"}
    sm = await client.get(a["urls"]["sm"])
    assert sm.status_code == 200 and sm.headers["content-type"] == "image/webp"
    assert sm.headers["x-content-type-options"] == "nosniff"
    img = Image.open(io.BytesIO(sm.content))
    assert img.format == "WEBP" and max(img.size) == 320
    lg = Image.open(io.BytesIO((await client.get(a["urls"]["lg"])).content))
    assert max(lg.size) == 1600
    small = (await upload(client, h, png_bytes((100, 50)))).json()
    assert Image.open(
        io.BytesIO((await client.get(small["urls"]["lg"])).content)
    ).size == (
        100,
        50,
    )  # no upscaling


async def test_exif_is_stripped(client):
    _, h = await make_user()
    im = Image.new("RGB", (50, 50), "red")
    exif = im.getexif()
    exif[0x010F] = "SecretCameraMaker"
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    a = (await upload(client, h, buf.getvalue(), "p.jpg", "image/jpeg")).json()
    served = (await client.get(a["urls"]["md"])).content
    assert (
        b"SecretCameraMaker" not in served
        and not Image.open(io.BytesIO(served)).getexif()
    )


async def test_signed_urls_expire_and_reject_tampering(client):
    _, h = await make_user()
    a = (await upload(client, h, png_bytes())).json()
    url = a["urls"]["sm"]
    assert (await client.get(url)).status_code == 200
    assert (
        await client.get(url[:-1] + ("0" if url[-1] != "0" else "1"))
    ).status_code == 404
    assert (
        await client.get(url.replace("/sm?", "/lg?"))
    ).status_code == 404  # sig covers the variant
    assert (await client.get(url.split("?")[0])).status_code == 422  # unsigned
    import uuid

    att = uuid.UUID(a["id"])
    past = 1_000_000
    signed = sign_media(att, "sm", now=past)
    exp, sig = [p.split("=")[1] for p in signed.split("?")[1].split("&")]
    assert verify_media(att, "sm", int(exp), sig, now=past)
    assert not verify_media(att, "sm", int(exp), sig, now=int(exp) + 1)
    assert not verify_media(att, "md", int(exp), sig, now=past)


@pytest.mark.parametrize(
    "name,mime,data",
    [
        ("evil.png", "image/png", b"MZ\x90\x00 this is an executable"),
        (
            "x.svg",
            "image/svg+xml",
            b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>",
        ),
        ("x.html", "image/png", b"<html><script>alert(1)</script></html>"),
        ("empty.png", "image/png", b""),
        ("x.zip", "application/zip", b"PK\x03\x04rest"),
    ],
)
async def test_content_sniffing_beats_the_claimed_type(client, name, mime, data):
    _, h = await make_user()
    r = await upload(client, h, data, name, mime)
    assert r.status_code == 415 and r.json()["code"] == "unsupported_media_type"


async def test_png_header_with_garbage_body_is_refused(client):
    _, h = await make_user()
    r = await upload(client, h, b"\x89PNG\r\n\x1a\n" + b"garbage" * 10)
    assert r.status_code == 422 and r.json()["code"] == "invalid_image"


async def test_size_limits(client, monkeypatch):
    from app.core.config import settings

    _, h = await make_user()
    monkeypatch.setattr(settings, "IMAGE_MAX_BYTES", 500)
    r = await upload(client, h, png_bytes((300, 300)))
    assert r.status_code == 413
    monkeypatch.setattr(settings, "UPLOAD_MAX_BYTES", 100)
    r = await upload(client, h, b"%PDF-1.4 " + b"x" * 200, "a.pdf", "application/pdf")
    assert r.status_code == 413


async def test_pdf_is_served_as_download_only(client):
    _, h = await make_user()
    r = await upload(
        client, h, b"%PDF-1.4 hello", "Lecture 1 (final).pdf", "application/pdf"
    )
    a = r.json()
    assert (
        a["kind"] == "file"
        and a["mime"] == "application/pdf"
        and set(a["urls"]) == {"file"}
    )
    got = await client.get(a["urls"]["file"])
    assert got.content == b"%PDF-1.4 hello"
    assert got.headers["content-disposition"].startswith("attachment")
    # PDFs are not allowed as avatars or covers
    assert (
        await upload(client, h, b"%PDF-1.4 x", "a.pdf", "application/pdf", "avatar")
    ).status_code == 415


async def test_virus_scan_hook_can_reject(client):
    from app.core.errors import AppError
    from app.services import uploads

    async def deny(data, mime):
        raise AppError("Infected.", code="infected", status_code=422)

    _, h = await make_user()
    uploads.set_scanner(deny)
    try:
        r = await upload(client, h, png_bytes())
    finally:
        uploads.set_scanner(uploads._no_scan)
    assert r.status_code == 422 and r.json()["code"] == "infected"
    assert (await upload(client, h, png_bytes())).status_code == 201


async def test_avatar_lives_in_storage_replaces_the_old_one(client):
    _, h = await make_user()
    r1 = await upload(client, h, png_bytes((300, 200)), purpose="avatar")
    assert r1.status_code == 201 and set(r1.json()["urls"]) == {"sm", "md"}
    me = (await client.get("/api/auth/me", headers=h)).json()
    assert me["avatar_url"] and me["avatar_url"].startswith("/api/media/")
    img = Image.open(io.BytesIO((await client.get(me["avatar_url"])).content))
    assert img.size == (64, 64)  # square crop
    old = r1.json()["urls"]["md"]
    r2 = await upload(client, h, png_bytes((100, 100), (0, 0, 255)), purpose="avatar")
    assert (await client.get(old)).status_code == 404  # replaced file is deleted
    assert (await client.get("/api/auth/me", headers=h)).json()["avatar_url"] != me[
        "avatar_url"
    ]
    assert r2.status_code == 201


async def test_permissions_and_rate_limit(client):
    assert (
        await client.post(
            "/api/uploads", files={"file": ("a.png", png_bytes(), "image/png")}
        )
    ).status_code == 401
    _, unverified = await make_user(verified=False)
    assert (await upload(client, unverified, png_bytes())).status_code == 403
    _, muted = await make_user(status="muted")
    assert (await upload(client, muted, png_bytes())).status_code == 403
    _, h = await make_user()
    codes = [(await upload(client, h, png_bytes())).status_code for _ in range(12)]
    assert codes.count(201) == 10 and codes[-1] == 429


async def test_resource_can_carry_an_attachment_and_previews_are_queued(client):
    from app.core import jobs
    from tests.factories import make_resource

    _, h = await make_user("verified_ufazian")
    a = (
        await upload(client, h, b"%PDF-1.4 notes", "notes.pdf", "application/pdf")
    ).json()
    jobs.enqueued.clear()
    res = await make_resource(client, h, primary_attachment_id=a["id"])
    assert res["attachment"]["name"] == "notes.pdf"
    assert [j[0] for j in jobs.enqueued] == ["fetch_link_preview"]
    _, other = await make_user("verified_ufazian")
    r = await client.post(
        "/api/resources",
        json={
            **__import__("tests.factories", fromlist=["x"]).resource_payload(),
            "primary_attachment_id": a["id"],
        },
        headers=other,
    )
    assert r.status_code == 422
