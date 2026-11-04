"""Operational behavior: request correlation, response hardening, shutdown and health."""

import io
import json
import subprocess
import sys
import threading
import time

import pytest
from fastapi.testclient import TestClient
from pv3d import __version__
from pv3d.app import JobRunner, create_app
from pv3d.config import Settings, SettingsError
from pv3d.observability import JsonFormatter, configure_logging
from pv3d.schemas import JobRequest
from pv3d.store import SCHEMA_VERSION, SchemaError, Store
from test_api import DetectorDouble, factory, picture, terminal, upload


def upload_bytes():
    return picture()


def test_health_reports_version_and_queue_capacity(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        payload = client.get("/api/health").json()
        assert payload["status"] == "ok" and payload["version"] == __version__
        assert payload["queue"] == {"max_pending": 8, "in_flight": 0, "available": 8}


def test_api_responses_carry_request_id_and_hardening_headers(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        response = client.get("/api/health")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "same-origin"
        assert response.headers["cache-control"] == "no-store"
        generated = response.headers["x-request-id"]
        assert len(generated) == 32
        echoed = client.get("/api/health", headers={"X-Request-ID": "trace-42.a"})
        assert echoed.headers["x-request-id"] == "trace-42.a"
        rejected = client.get("/api/health", headers={"X-Request-ID": "bad id\twith control"})
        assert rejected.headers["x-request-id"] != "bad id\twith control"
        assert "x-request-id" in client.get("/api/nothing-here").headers


def test_binary_api_responses_are_not_marked_no_store(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        response = client.get(asset["image_url"])
        assert response.status_code == 200
        assert response.headers.get("cache-control") != "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"


def test_cors_is_off_by_default_and_opt_in_per_origin(tmp_path):
    preflight = {"Origin": "https://ops.example", "Access-Control-Request-Method": "GET"}
    with TestClient(factory(tmp_path)) as client:
        assert "access-control-allow-origin" not in client.options("/api/health", headers=preflight).headers
    settings = Settings.from_env({"PV3D_CORS_ORIGINS": "https://ops.example"})
    with TestClient(create_app(tmp_path, DetectorDouble(), settings=settings)) as client:
        allowed = client.options("/api/health", headers=preflight)
        assert allowed.headers["access-control-allow-origin"] == "https://ops.example"
        denied = client.options("/api/health", headers={**preflight, "Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in denied.headers


def test_queue_limit_is_configurable_through_settings(tmp_path):
    release = threading.Event()
    settings = Settings.from_env({"PV3D_MAX_PENDING_JOBS": "2"})
    try:
        with TestClient(create_app(tmp_path, DetectorDouble(release=release), settings=settings)) as client:
            asset = upload(client)
            codes = [client.post("/api/jobs", json={"asset_id": asset["id"]}).status_code for _ in range(3)]
            assert codes == [202, 202, 409]
            assert client.get("/api/health").json()["queue"] == {"max_pending": 2, "in_flight": 2, "available": 0}
            release.set()
    finally:
        release.set()


def test_missing_mask_file_is_a_404_not_a_server_error(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        identifier = "f" * 32
        client.app.state.store.add_refinement(
            {"id": identifier, "asset_id": asset["id"], "mask_polygons": [], "geometry_bbox": [0, 0, 1, 1]}
        )
        response = client.get(f"/api/refinements/{identifier}/mask.png")
        assert response.status_code == 404
        assert "unavailable" in response.json()["detail"]


def test_shutdown_finishes_running_work_and_interrupts_queued_jobs(tmp_path):
    release = threading.Event()
    store = Store(tmp_path)
    runner = JobRunner(store, DetectorDouble(release=release))
    asset = {"id": "a" * 32, "width": 8, "height": 8, "sha256": "0" * 64}
    (tmp_path / "assets" / asset["id"]).mkdir(parents=True)
    from PIL import Image

    Image.new("RGB", (8, 8), "#123456").save(tmp_path / "assets" / asset["id"] / "image.jpg")
    store.add_asset(asset)
    running = runner.submit(JobRequest(asset_id=asset["id"]))
    queued = runner.submit(JobRequest(asset_id=asset["id"]))
    deadline = time.monotonic() + 5
    while store.get_job(running["id"])["status"] != "running" and time.monotonic() < deadline:
        time.sleep(0.01)
    closer = threading.Thread(target=runner.close)
    closer.start()
    time.sleep(0.2)
    release.set()
    closer.join(timeout=10)
    assert not closer.is_alive()
    assert store.get_job(running["id"])["status"] == "needs_review"
    interrupted = store.get_job(queued["id"])
    assert interrupted["status"] == "interrupted" and interrupted["error"]
    with pytest.raises(Exception) as excinfo:
        runner.submit(JobRequest(asset_id=asset["id"]))
    assert getattr(excinfo.value, "status_code", None) == 503
    assert store.get_job(queued["id"])["status"] == "interrupted"


def test_jobs_complete_normally_when_the_server_stays_up(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        job = client.post("/api/jobs", json={"asset_id": asset["id"]}).json()
        assert terminal(client, job["id"])["status"] == "needs_review"


def test_store_records_schema_version_and_refuses_newer_ledgers(tmp_path):
    store = Store(tmp_path)
    assert store.schema_version == SCHEMA_VERSION
    import sqlite3

    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION + 1}")
    with pytest.raises(SchemaError, match="schema"):
        Store(tmp_path)


def test_json_log_lines_include_extra_fields_and_are_single_line(capsys):
    import logging

    configure_logging("INFO", "json")
    logging.getLogger("pv3d.test").info("hello %s", "world", extra={"request_id": "r1", "duration_ms": 1.5})
    line = capsys.readouterr().err.strip()
    payload = json.loads(line)
    assert payload["message"] == "hello world" and payload["request_id"] == "r1"
    assert payload["duration_ms"] == 1.5 and payload["level"] == "INFO" and "\n" not in line
    assert isinstance(JsonFormatter().format(logging.makeLogRecord({"msg": "x", "levelname": "INFO"})), str)
    configure_logging("WARNING", "text")


def test_access_log_records_method_path_status_and_request_id(tmp_path, caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="pv3d.access"), TestClient(factory(tmp_path)) as client:
        client.get("/api/health", headers={"X-Request-ID": "trace-7"})
    records = [r for r in caplog.records if r.name == "pv3d.access"]
    assert any(r.request_id == "trace-7" and r.status == 200 and r.path == "/api/health" for r in records)


def test_server_entry_point_validates_settings_without_binding(tmp_path):
    env = {"PV3D_DATA_DIR": str(tmp_path), "PATH": "", "PV3D_PORT": "8010"}
    ok = subprocess.run(
        [sys.executable, "-m", "pv3d", "--check"], capture_output=True, text=True, env=env, timeout=60, check=False
    )
    assert ok.returncode == 0, ok.stderr
    assert "port=8010" in ok.stdout
    bad = subprocess.run(
        [sys.executable, "-m", "pv3d", "--check"],
        capture_output=True, text=True, env={**env, "PV3D_PORT": "nope"}, timeout=60, check=False,
    )
    assert bad.returncode == 2 and "PV3D_PORT" in bad.stderr


def test_second_server_on_the_same_data_directory_is_refused(tmp_path):
    from pv3d.store import DataDirectoryLock, LockedDataDirectoryError

    with TestClient(factory(tmp_path)) as first:
        assert first.get("/api/health").status_code == 200
        with pytest.raises(LockedDataDirectoryError, match="PV3D_DATA_DIR"):
            with TestClient(factory(tmp_path)):
                pass
        with pytest.raises(LockedDataDirectoryError):
            DataDirectoryLock(tmp_path).acquire()
    # Released on shutdown: the next server starts normally and a direct Store still works.
    with TestClient(factory(tmp_path)) as second:
        assert second.get("/api/health").status_code == 200
        Store(tmp_path)


def test_oversized_declared_upload_is_refused_before_parsing(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        huge = b"\x00" * (21 * 1024 * 1024)
        response = client.post("/api/assets", files={"file": ("big.png", huge, "image/png")})
        assert response.status_code == 413
        assert "20 MB" in response.json()["detail"]
        ok = client.post("/api/assets", files={"file": ("photo.png", upload_bytes(), "image/png")})
        assert ok.status_code == 201


def test_uploads_without_content_length_are_refused_with_411(tmp_path):
    import asyncio

    from pv3d.observability import BodyLimitMiddleware

    seen = []

    async def downstream(scope, receive, send):
        seen.append(scope["path"])

    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    middleware = BodyLimitMiddleware(downstream, {"/api/assets": 10})
    scope = {"type": "http", "method": "POST", "path": "/api/assets", "headers": []}
    asyncio.run(middleware(scope, receive, send))
    assert sent[0]["status"] == 411 and not seen
    scope["headers"] = [(b"content-length", b"abc")]
    asyncio.run(middleware(scope, receive, send))
    assert sent[2]["status"] == 400
    scope["headers"] = [(b"content-length", b"5")]
    asyncio.run(middleware(scope, receive, send))
    assert seen == ["/api/assets"]
    asyncio.run(middleware({"type": "http", "method": "GET", "path": "/api/assets", "headers": []}, receive, send))
    assert seen == ["/api/assets", "/api/assets"]


def test_refinement_does_not_wait_forever_behind_a_long_job(tmp_path):
    release = threading.Event()
    settings = Settings.from_env({"PV3D_REFINE_TIMEOUT_S": "1"})
    try:
        with TestClient(create_app(tmp_path, DetectorDouble(release=release), settings=settings)) as client:
            asset = upload(client)
            assert client.post("/api/jobs", json={"asset_id": asset["id"]}).status_code == 202
            started = time.monotonic()
            response = client.post(
                "/api/refinements", json={"asset_id": asset["id"], "bbox": [0.1, 0.1, 0.5, 0.5]}
            )
            assert response.status_code == 503
            assert "busy" in response.json()["detail"]
            assert time.monotonic() - started < 5
            # The cancelled refinement released its slot: only the job remains in flight.
            assert client.get("/api/health").json()["queue"]["in_flight"] == 1
            release.set()
    finally:
        release.set()


def test_multi_picture_jpeg_is_accepted_as_jpeg(tmp_path):
    from PIL import Image

    data = io.BytesIO()
    first = Image.new("RGB", (64, 48), "#102030")
    first.save(data, format="MPO", append_images=[Image.new("RGB", (64, 48), "#405060")])
    with TestClient(factory(tmp_path)) as client:
        response = client.post("/api/assets", files={"file": ("depth.jpg", data.getvalue(), "image/jpeg")})
        assert response.status_code == 201, response.text
        assert response.json()["width"] == 64


def test_wrong_method_on_a_real_route_is_405_not_404(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        assert client.delete("/api/jobs/" + "a" * 32).status_code == 405
        assert client.get("/api/does-not-exist").status_code == 404
        assert client.post("/api/does-not-exist").status_code == 404


TOKEN = "s3cret-token-with-16+chars"


def token_app(tmp_path, **overrides):
    settings = Settings.from_env({"PV3D_API_TOKEN": TOKEN, **overrides})
    return create_app(tmp_path, DetectorDouble(), settings=settings)


def test_token_settings_are_validated():
    assert Settings.from_env({}).api_token is None and not Settings.from_env({}).requires_token
    assert Settings.from_env({"PV3D_API_TOKEN": "  "}).api_token is None
    with pytest.raises(SettingsError, match="PV3D_API_TOKEN"):
        Settings.from_env({"PV3D_API_TOKEN": "short"})
    with pytest.raises(SettingsError, match="PV3D_API_TOKEN"):
        Settings.from_env({"PV3D_API_TOKEN": "has a space in the token"})
    with pytest.raises(SettingsError, match="PV3D_SESSION_MAX_AGE_S"):
        Settings.from_env({"PV3D_API_TOKEN": TOKEN, "PV3D_SESSION_MAX_AGE_S": "5"})
    assert Settings.from_env({"PV3D_API_TOKEN": TOKEN}).requires_token


def test_without_a_token_the_api_stays_open_and_reports_no_authentication(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        assert client.get("/api/health").json()["authentication"] == "none"
        assert client.get("/api/session").status_code == 404
        assert upload(client)["id"]


def test_token_guards_every_api_route_except_health_and_session(tmp_path):
    with TestClient(token_app(tmp_path)) as client:
        health = client.get("/api/health")
        assert health.status_code == 200 and health.json()["authentication"] == "token"
        denied = client.post("/api/assets", files={"file": ("photo.png", picture(), "image/png")})
        assert denied.status_code == 401
        assert denied.headers["www-authenticate"].startswith("Bearer")
        assert "token" in denied.json()["detail"].lower()
        assert client.get("/api/jobs/" + "a" * 32).status_code == 401
        assert client.get("/api/session").json() == {"required": True, "authenticated": False}
        bearer = {"Authorization": f"Bearer {TOKEN}"}
        asset = client.post("/api/assets", files={"file": ("photo.png", picture(), "image/png")}, headers=bearer)
        assert asset.status_code == 201
        assert client.get(f"/api/assets/{asset.json()['id']}/image", headers=bearer).status_code == 200
        assert client.get("/api/jobs/" + "a" * 32, headers={"Authorization": f"Bearer {TOKEN}x"}).status_code == 401
        assert client.get("/api/jobs/" + "a" * 32, headers={"Authorization": f"Basic {TOKEN}"}).status_code == 401


def test_session_cookie_signs_in_the_browser_without_exposing_the_token(tmp_path):
    with TestClient(token_app(tmp_path)) as client:
        assert client.post("/api/session", json={"token": "wrong-token-value-123"}).status_code == 401
        assert client.post("/api/session", json={"token": TOKEN, "extra": 1}).status_code == 422
        created = client.post("/api/session", json={"token": TOKEN})
        assert created.status_code == 200 and created.json()["authenticated"] is True
        cookie = created.headers["set-cookie"].lower()
        assert "pv3d_session=" in cookie and "httponly" in cookie and "samesite=strict" in cookie
        assert TOKEN.lower() not in cookie
        # The client jar now carries the cookie: downloads and JSON routes work without a header.
        assert client.get("/api/session").json()["authenticated"] is True
        asset = upload(client)
        assert client.get(asset["image_url"]).status_code == 200
        assert client.delete("/api/session").json()["authenticated"] is False
        assert client.get("/api/jobs/" + "a" * 32).status_code == 401


def test_forged_or_malformed_cookies_are_rejected(tmp_path):
    with TestClient(token_app(tmp_path)) as client:
        for cookie in ("pv3d_session=forged", f"pv3d_session={TOKEN}", "garbage;;=;", "pv3d_session="):
            response = client.get("/api/jobs/" + "a" * 32, headers={"Cookie": cookie})
            assert response.status_code == 401, cookie


def test_unauthenticated_uploads_are_refused_before_the_body_is_parsed(tmp_path):
    with TestClient(token_app(tmp_path)) as client:
        huge = b"\x00" * (2 * 1024 * 1024)
        assert client.post("/api/assets", files={"file": ("big.png", huge, "image/png")}).status_code == 401
        assert "x-request-id" in client.get("/api/jobs/" + "a" * 32).headers


def test_static_web_app_stays_reachable_but_api_calls_need_the_token(tmp_path):
    with TestClient(token_app(tmp_path)) as client:
        assert client.get("/api/nothing").status_code == 401
        assert client.get("/api/health").status_code == 200
