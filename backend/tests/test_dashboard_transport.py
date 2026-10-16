"""Explicit dashboard origin, bounded browser sessions and private schema export."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from victus.api.app import create_app
from victus.api.auth import COOKIE, PRODUCTION_ORIGIN, BrowserSessions
from victus.settings import Settings

TOKEN = "dashboard-test-" + "x" * 40
AUTH = {"Authorization": "Bearer " + TOKEN}
ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(Settings(tmp_path, TOKEN, dashboard_dev_origin=ORIGIN)),
        base_url=PRODUCTION_ORIGIN,
    ) as test_client:
        yield test_client


def test_only_chosen_dev_origin_and_headers_pass_preflight(client):
    response = client.options(
        "/api/tasks",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,x-request-id,x-client-request-id",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    response = client.get(
        "/api/health", headers={**AUTH, "Origin": ORIGIN, "X-Request-ID": "trace-1"}
    )
    assert response.status_code == 200 and response.headers["X-Request-ID"] == "trace-1"
    assert response.headers["Cache-Control"] == "no-store"
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]
    assert client.get("/api/health", headers={"Origin": ORIGIN}).status_code == 401


@pytest.mark.parametrize(
    "origin", ["http://localhost:5173", "http://127.0.0.1:5174", "https://evil.test", "null"]
)
def test_other_origins_cannot_read_or_mutate(client, origin):
    response = client.post("/api/stop", headers={**AUTH, "Origin": origin})
    assert response.status_code == 403 and "access-control-allow-origin" not in response.headers
    assert not client.app.state.services.tasks.stopped.is_set()
    preflight = client.options(
        "/api/stop", headers={"Origin": origin, "Access-Control-Request-Method": "POST"}
    )
    assert preflight.status_code == 400


def test_development_origin_requires_explicit_opt_in(tmp_path):
    with TestClient(create_app(Settings(tmp_path, TOKEN)), base_url=PRODUCTION_ORIGIN) as client:
        assert client.get("/api/health", headers={**AUTH, "Origin": ORIGIN}).status_code == 403


@pytest.mark.parametrize(
    "origin", ["*", "http://0.0.0.0:5173", "http://localhost:5173", "http://127.0.0.1:5174"]
)
def test_settings_refuse_unknown_development_hosts_and_ports(tmp_path, origin):
    with pytest.raises(ValueError):
        Settings(tmp_path, TOKEN, dashboard_dev_origin=origin)


def test_bearer_bootstrap_cookie_csrf_expiry_and_logout(client):
    now = [time.time()]
    client.app.state.browser_sessions.clock = lambda: now[0]
    assert client.post("/api/session", headers={"Origin": PRODUCTION_ORIGIN}).status_code == 401
    response = client.post("/api/session", headers={**AUTH, "Origin": PRODUCTION_ORIGIN})
    assert response.status_code == 200
    cookie_header = response.headers["set-cookie"].lower()
    assert (
        "httponly" in cookie_header
        and "samesite=strict" in cookie_header
        and "path=/api" in cookie_header
    )
    assert TOKEN not in response.text and COOKIE not in response.text
    assert client.get("/api/health").status_code == 200
    assert (
        client.get("/api/health", headers={"Authorization": "Bearer incorrect"}).status_code == 401
    )
    assert client.post("/api/stop").status_code == 403
    assert client.post("/api/stop", headers={"Origin": ORIGIN}).status_code == 403
    assert client.get("/api/session").json()["expires_at"] == response.json()["expires_at"]
    assert client.delete("/api/session", headers={"Origin": PRODUCTION_ORIGIN}).status_code == 204
    assert client.get("/api/health").status_code == 401
    client.post("/api/session", headers={**AUTH, "Origin": PRODUCTION_ORIGIN})
    now[0] += 901
    assert client.get("/api/health").status_code == 401


def test_cookie_works_for_same_origin_mutations(client):
    client.post("/api/session", headers={**AUTH, "Origin": PRODUCTION_ORIGIN})
    assert client.post("/api/stop", headers={"Origin": PRODUCTION_ORIGIN}).status_code == 200


def test_browser_sessions_are_bounded_and_do_not_persist_the_token():
    now = [100.0]
    sessions = BrowserSessions(clock=lambda: now[0], capacity=1)
    token, expiry = sessions.create()
    assert token not in sessions._sessions
    assert sessions.expiry(token) == expiry
    with pytest.raises(Exception) as error:
        sessions.create()
    assert error.value.status_code == 429
    now[0] = expiry
    assert sessions.expiry(token) is None
    sessions.create()


@pytest.mark.parametrize("path", ["/openapi.json", "/docs", "/redoc"])
def test_openapi_has_no_public_route(client, path):
    assert client.get(path).status_code == 404
    assert client.get(path, headers=AUTH).status_code == 404


def test_build_time_export_needs_no_token_or_running_service(tmp_path, monkeypatch):
    import victus.api.app as module
    from victus.cli import main

    monkeypatch.setattr(
        module, "build_services", lambda *_: pytest.fail("Schema export started services")
    )
    monkeypatch.setenv("VICTUS_API_TOKEN", "PRIVATE_MUST_NOT_APPEAR")
    output = tmp_path / "openapi.json"
    monkeypatch.setattr("sys.argv", ["victus", "export-openapi", "--output", str(output)])
    main()
    schema = json.loads(output.read_text())
    assert "PRIVATE_MUST_NOT_APPEAR" not in output.read_text()
    assert schema["paths"]["/api/health"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/HealthResponse")
    assert schema["paths"]["/api/tasks"]["post"]["security"]
    assert set(schema["components"]["securitySchemes"]) == {"HTTPBearer", "APIKeyCookie"}


def test_backend_serves_only_built_dashboard_and_keeps_api_protected(tmp_path):
    dist = tmp_path / "dashboard-build"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html><h1>VICTUS fixture</h1></html>")
    (dist / "assets" / "app.js").write_text("void 0")
    with TestClient(
        create_app(Settings(tmp_path / "data", TOKEN, dashboard_dir=dist)),
        base_url=PRODUCTION_ORIGIN,
    ) as client:
        assert client.get("/").status_code == 200
        assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/src/api/client.ts").status_code == 404
        assert client.get("/api/health").status_code == 401
