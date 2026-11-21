async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["x-request-id"]


async def test_request_id_is_echoed_when_safe(client):
    r = await client.get("/api/health", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"
    r = await client.get("/api/health", headers={"X-Request-ID": "bad id\nx"})
    assert r.headers["x-request-id"] != "bad id\nx"


async def test_ready_reports_db(client):
    r = await client.get("/api/ready")
    assert r.json()["db"] == "ok"


async def test_error_envelope_on_404(client):
    r = await client.get("/api/nope", headers={"X-Request-ID": "rid1"})
    assert r.status_code == 404
    assert r.json() == {
        "code": "not_found",
        "message": "Not Found",
        "request_id": "rid1",
    }
