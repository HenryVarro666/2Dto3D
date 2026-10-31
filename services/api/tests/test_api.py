"""HTTP behavior with real files/SQLite/GLB and a controlled slow-model boundary."""

import io
import json
import sqlite3
import struct
import threading
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image


class DetectorDouble:
    def __init__(self, detections=(), *, release=None, failure=None):
        self.detections = list(detections)
        self.release = release
        self.failure = failure

    def status(self):
        return {"state": "ready", "model_id": "boundary-only", "device": "cpu"}

    def detect(self, image, on_progress=None, scene_mode="single"):
        if self.release is not None:
            assert self.release.wait(5), "test did not release detector"
        if self.failure:
            raise self.failure
        return {
            "detections": self.detections,
            "model": {"model_id": "boundary-only", "revision": "test", "device": "cpu"},
            "timings": {"inference_ms": 1.0},
            "warnings": [],
        }


def picture(size=(320, 200), fmt="PNG", exif=None):
    data = io.BytesIO()
    kwargs = {"exif": exif} if exif is not None else {}
    Image.new("RGB", size, "#476480").save(data, format=fmt, **kwargs)
    return data.getvalue()


def upload(client, data=None):
    response = client.post("/api/assets", files={"file": ("photo.png", data or picture(), "image/png")})
    assert response.status_code == 201, response.text
    return response.json()


def terminal(client, job_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.01)
    pytest.fail("job did not reach a terminal state")


def factory(tmp_path, detector=None):
    from pv3d.app import create_app

    return create_app(data_dir=tmp_path, detector=detector or DetectorDouble())


def test_job_scope_reaches_detector_and_is_recorded_without_changing_v1_default(tmp_path):
    seen = []

    class ScopeDetector(DetectorDouble):
        def detect(self, image, on_progress=None, scene_mode="single"):
            seen.append(scene_mode)
            return super().detect(image, on_progress=on_progress)

    with TestClient(factory(tmp_path, ScopeDetector())) as client:
        asset = upload(client)
        for body, expected in [({}, "single"), ({"scene_mode": "multiple"}, "multiple")]:
            response = client.post("/api/jobs", json={"asset_id": asset["id"], **body})
            assert response.status_code == 202, response.text
            result = terminal(client, response.json()["id"])["result"]
            assert result["scene_mode"] == expected
        assert seen == ["single", "multiple"]
        assert (
            client.post("/api/jobs", json={"asset_id": asset["id"], "scene_mode": "any"}).status_code == 422
        )


def test_upload_rejects_invalid_image_without_persisting_asset(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        response = client.post(
            "/api/assets", files={"file": ("looks-valid.jpg", b"not an image", "image/jpeg")}
        )
        assert response.status_code == 400
        assert not list((tmp_path / "assets").glob("*/image.jpg"))


@pytest.mark.parametrize("payload", [picture(fmt="GIF"), b"x" * (20 * 1024 * 1024 + 1)])
def test_upload_rejects_unsupported_or_oversized_content(tmp_path, payload):
    with TestClient(factory(tmp_path)) as client:
        response = client.post("/api/assets", files={"file": ("photo.png", payload, "image/png")})
        assert response.status_code in {400, 413}


def test_upload_rejects_decoded_pixel_limit(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        response = client.post(
            "/api/assets", files={"file": ("large.png", picture((5001, 5000)), "image/png")}
        )
        assert response.status_code == 413


def test_upload_orients_resizes_and_serves_normalized_image(tmp_path):
    exif = Image.Exif()
    exif[274] = 6
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client, picture((2400, 1200), "JPEG", exif))
        assert [asset["width"], asset["height"]] == [1024, 2048]
        assert len(asset["sha256"]) == 64
        assert asset["image_url"].startswith("/api/assets/")
        assert str(tmp_path) not in json.dumps(asset)
        response = client.get(asset["image_url"])
        assert response.status_code == 200
        with Image.open(io.BytesIO(response.content)) as normalized:
            assert normalized.size == (1024, 2048)
            assert normalized.getexif().get(274, 1) == 1


def test_empty_recognition_requires_review_and_has_no_scene(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        response = client.post("/api/jobs", json={"asset_id": asset["id"]})
        assert response.status_code == 202
        job = terminal(client, response.json()["id"])
        assert job["status"] == "needs_review"
        assert job["result"]["components"] == []
        assert job["result"]["scene_url"] is None
        assert client.get(f"/api/jobs/{job['id']}/scene.glb").status_code == 409
        assert client.get(job["result"]["json_url"]).json() == job["result"]


def test_running_job_is_pollable_and_result_is_409(tmp_path):
    release = threading.Event()
    try:
        with TestClient(factory(tmp_path, DetectorDouble(release=release))) as client:
            asset = upload(client)
            response = client.post("/api/jobs", json={"asset_id": asset["id"]})
            job_id = response.json()["id"]
            assert client.get(f"/api/jobs/{job_id}").json()["status"] in {"queued", "running"}
            assert client.get(f"/api/jobs/{job_id}/result").status_code == 409
            release.set()
            assert terminal(client, job_id)["status"] == "needs_review"
    finally:
        release.set()


def test_real_stage_reports_are_pollable_before_the_model_returns(tmp_path):
    stages = ["loading_model", "detecting", "loading_segmentation", "segmenting"]
    entered = {stage: threading.Event() for stage in stages}
    release = {stage: threading.Event() for stage in stages}

    class StagedDetector(DetectorDouble):
        def detect(self, image, on_progress=None, scene_mode="single"):
            assert callable(on_progress), "the runner must forward real model progress"
            for stage in stages:
                on_progress(stage)
                entered[stage].set()
                assert release[stage].wait(5)
            return super().detect(image)

    with TestClient(factory(tmp_path, StagedDetector())) as client:
        asset = upload(client)
        job_id = client.post("/api/jobs", json={"asset_id": asset["id"]}).json()["id"]
        try:
            for stage in stages:
                assert entered[stage].wait(2), client.get(f"/api/jobs/{job_id}").json()
                job = client.get(f"/api/jobs/{job_id}").json()
                assert job["status"] == "running"
                assert job["stage"] == stage
                release[stage].set()
            assert terminal(client, job_id)["status"] == "needs_review"
        finally:
            for gate in release.values():
                gate.set()


def test_failed_job_retains_the_actual_processing_stage(tmp_path):
    class FailingDetector(DetectorDouble):
        def detect(self, image, on_progress=None, scene_mode="single"):
            if on_progress:
                on_progress("detecting")
            raise RuntimeError("transient model failure")

    with TestClient(factory(tmp_path, FailingDetector())) as client:
        asset = upload(client)
        job_id = client.post("/api/jobs", json={"asset_id": asset["id"]}).json()["id"]
        job = terminal(client, job_id)
        assert job["status"] == "failed"
        assert job["stage"] == "detecting"


def test_model_failure_is_durable_and_does_not_leak_internal_paths(tmp_path):
    app = factory(tmp_path, DetectorDouble(failure=RuntimeError("secret /Users/someone/model.bin")))
    with TestClient(app) as client:
        asset = upload(client)
        response = client.post("/api/jobs", json={"asset_id": asset["id"]})
        job_id = response.json()["id"]
        failed = terminal(client, job_id)
        assert failed["status"] == "failed"
        assert failed["error"]
        assert "/Users/" not in json.dumps(failed)
    with TestClient(factory(tmp_path)) as client:
        assert client.get(f"/api/jobs/{job_id}").json() == failed
        assert client.get(asset["image_url"]).status_code == 200


def test_restart_marks_persisted_unfinished_job_interrupted(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        job_id = client.post("/api/jobs", json={"asset_id": asset["id"]}).json()["id"]
        terminal(client, job_id)
    # Simulate a process crash after it persisted 'running', without a live worker.
    db = next(tmp_path.glob("*.sqlite3"))
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE jobs SET status = 'running', stage = 'recognition', result_json = NULL WHERE id = ?",
            (job_id,),
        )
    with TestClient(factory(tmp_path)) as client:
        job = client.get(f"/api/jobs/{job_id}").json()
        assert job["status"] == "interrupted"
        assert job["result"] is None
        assert job["error"]
        assert client.get(f"/api/jobs/{job_id}/result").status_code == 409


def test_manual_rebuild_preserves_ids_and_creates_new_scene_without_overwriting(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        original_id = client.post("/api/jobs", json={"asset_id": asset["id"]}).json()["id"]
        original = terminal(client, original_id)
        response = client.post(
            "/api/jobs",
            json={
                "asset_id": asset["id"],
                "mode": "manual",
                "components": [
                    {
                        "id": "cabinet-01",
                        "category": "cabinet",
                        "label": "Inverter",
                        "bbox": [0.3, 0.1, 0.7, 0.8],
                    },
                    {
                        "id": "support-01",
                        "category": "pole",
                        "label": "Visible pole",
                        "bbox": [0.73, 0.1, 0.8, 0.9],
                    },
                ],
            },
        )
        assert response.status_code == 202, response.text
        rebuilt = terminal(client, response.json()["id"])
        assert rebuilt["id"] != original_id
        assert rebuilt["status"] == "succeeded"
        result = client.get(f"/api/jobs/{rebuilt['id']}/result").json()
        assert [component["id"] for component in result["components"]] == ["cabinet-01", "support-01"]
        assert all(component["source"] == "manual" for component in result["components"])
        assert all(component["score"] is None for component in result["components"])
        scene = client.get(result["scene_url"])
        assert scene.status_code == 200
        assert scene.content[:4] == b"glTF"
        assert struct.unpack_from("<I", scene.content, 4)[0] == 2
        assert client.get(result["json_url"]).json() == result
        assert client.get(f"/api/jobs/{original_id}").json() == original


@pytest.mark.parametrize(
    "component",
    [
        {"category": "cabinet", "label": "x", "bbox": [0.5, 0, 0.2, 1]},
        {"category": "cabinet", "label": "x", "bbox": [-0.01, 0, 0.2, 1]},
        {"category": "cabinet", "label": "x", "bbox": [0, 0, 1, 2]},
        {"category": "not-in-profile", "label": "x", "bbox": [0, 0, 1, 1]},
        {"id": "../../outside", "category": "cabinet", "label": "x", "bbox": [0, 0, 1, 1]},
    ],
)
def test_invalid_manual_components_are_rejected_before_job_creation(tmp_path, component):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        response = client.post(
            "/api/jobs", json={"asset_id": asset["id"], "mode": "manual", "components": [component]}
        )
        assert response.status_code == 422


def test_duplicate_manual_ids_and_implicit_manual_payload_are_rejected(tmp_path):
    component = {"id": "same", "category": "cabinet", "label": "x", "bbox": [0, 0, 1, 1]}
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        duplicate = client.post(
            "/api/jobs",
            json={"asset_id": asset["id"], "mode": "manual", "components": [component, component]},
        )
        assert duplicate.status_code == 422
        automatic = client.post("/api/jobs", json={"asset_id": asset["id"], "components": [component]})
        assert automatic.status_code == 422


def test_unknown_or_malformed_resource_ids_never_serve_paths(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        assert client.get("/api/assets/missing/image").status_code == 404
        assert client.get("/api/jobs/missing").status_code == 404
        assert client.get("/api/jobs/missing/result").status_code == 404
        assert client.get("/api/jobs/missing/scene.glb").status_code == 404
        assert client.get("/api/assets/%2E%2E/image").status_code == 404
        assert client.post("/api/jobs", json={"asset_id": "missing"}).status_code == 404
        assert client.get("/api/does-not-exist").status_code == 404


def test_nonfinite_bbox_is_a_validation_error_instead_of_server_failure(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        payload = {
            "asset_id": asset["id"],
            "mode": "manual",
            "components": [{"category": "cabinet", "label": "x", "bbox": [0, 0, float("nan"), 1]}],
        }
        response = client.post(
            "/api/jobs", content=json.dumps(payload), headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


def test_recognized_bbox_and_evidence_survive_actual_api_to_glb_pipeline(tmp_path):
    candidate = {
        "category": "cabinet",
        "label": "Inverter cabinet",
        "bbox": [0.2, 0.15, 0.75, 0.8],
        "score": 0.82,
        "source": "grounding_dino",
        "mask_polygon": None,
    }
    with TestClient(factory(tmp_path, DetectorDouble([candidate]))) as client:
        asset = upload(client)
        job = client.post("/api/jobs", json={"asset_id": asset["id"]}).json()
        result = terminal(client, job["id"])["result"]
        component = result["components"][0]
        assert component["bbox"] == [0.2, 0.15, 0.75, 0.8]
        assert component["score"] == 0.82
        assert component["source"] == "grounding_dino"
        assert component["mask_polygon"] is None
        assert component["dimensions"][1] == pytest.approx(2)
        assert result["metric_scale_status"] == "unknown"
        assert client.get(result["scene_url"]).content[:4] == b"glTF"


def test_single_worker_queue_is_bounded_and_excess_work_is_not_persisted(tmp_path):
    release = threading.Event()
    try:
        with TestClient(factory(tmp_path, DetectorDouble(release=release))) as client:
            asset = upload(client)
            responses = [client.post("/api/jobs", json={"asset_id": asset["id"]}) for _ in range(9)]
            assert [response.status_code for response in responses] == [202] * 8 + [409]
            db = next(tmp_path.glob("*.sqlite3"))
            with sqlite3.connect(db) as connection:
                assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 8
                assert (
                    connection.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0] <= 1
                )
            release.set()
            assert terminal(client, responses[-2].json()["id"])["status"] == "needs_review"
    finally:
        release.set()


def test_manual_rebuild_preserves_unchanged_detection_evidence_from_same_asset_base(tmp_path):
    candidates = [
        {
            "id": "inverter",
            "category": "cabinet",
            "label": "Inverter",
            "bbox": [0.2, 0.1, 0.7, 0.7],
            "score": 0.91,
            "source": "grounding_dino",
            "mask_polygon": [[0.2, 0.1], [0.7, 0.1], [0.7, 0.7]],
        },
        {
            "id": "support",
            "category": "pole",
            "label": "Pole",
            "bbox": [0.75, 0.1, 0.82, 0.9],
            "score": 0.78,
            "source": "grounding_dino",
            "mask_polygon": [[0.75, 0.1], [0.82, 0.1], [0.82, 0.9]],
        },
    ]
    with TestClient(factory(tmp_path, DetectorDouble(candidates))) as client:
        asset = upload(client)
        base_id = client.post("/api/jobs", json={"asset_id": asset["id"]}).json()["id"]
        original = terminal(client, base_id)
        response = client.post(
            "/api/jobs",
            json={
                "asset_id": asset["id"],
                "mode": "manual",
                "base_job_id": base_id,
                "components": [
                    {
                        "id": "inverter",
                        "category": "cabinet",
                        "label": "Renamed cabinet",
                        "bbox": [0.2, 0.1, 0.7, 0.7],
                    },
                    {"id": "support", "category": "pole", "label": "Pole", "bbox": [0.75, 0.1, 0.82, 0.9]},
                    {
                        "id": "added",
                        "category": "cables",
                        "label": "New cables",
                        "bbox": [0.4, 0.7, 0.6, 0.95],
                    },
                ],
            },
        )
        assert response.status_code == 202, response.text
        rebuilt = terminal(client, response.json()["id"])["result"]
        renamed, unchanged, added = rebuilt["components"]
        assert renamed["source"] == "manual"
        assert renamed["score"] is None
        assert renamed["mask_polygon"] == [[0.2, 0.1], [0.7, 0.1], [0.7, 0.7]]
        assert unchanged["source"] == "grounding_dino"
        assert unchanged["score"] == 0.78
        assert unchanged["mask_polygon"] == [[0.75, 0.1], [0.82, 0.1], [0.82, 0.9]]
        assert added["source"] == "manual"
        assert added["score"] is None
        assert client.get(f"/api/jobs/{base_id}").json() == original


def test_manual_base_job_must_exist_be_complete_and_match_asset(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        other_asset = upload(client)
        base_id = client.post("/api/jobs", json={"asset_id": asset["id"]}).json()["id"]
        terminal(client, base_id)
        for bad_base, target, expected in [
            ("missing", asset["id"], 404),
            ("../../internal", asset["id"], 404),
            (base_id, other_asset["id"], 400),
        ]:
            response = client.post(
                "/api/jobs",
                json={
                    "asset_id": target,
                    "mode": "manual",
                    "base_job_id": bad_base,
                    "components": [],
                },
            )
            assert response.status_code == expected, response.text
        automatic = client.post("/api/jobs", json={"asset_id": asset["id"], "base_job_id": base_id})
        assert automatic.status_code == 422
        db = next(tmp_path.glob("*.sqlite3"))
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE jobs SET status='failed', result_json=NULL WHERE id=?", (base_id,))
        unfinished = client.post(
            "/api/jobs",
            json={
                "asset_id": asset["id"],
                "mode": "manual",
                "base_job_id": base_id,
                "components": [],
            },
        )
        assert unfinished.status_code == 409


def test_manual_components_cannot_forge_model_provenance(tmp_path):
    with TestClient(factory(tmp_path)) as client:
        asset = upload(client)
        response = client.post(
            "/api/jobs",
            json={
                "asset_id": asset["id"],
                "mode": "manual",
                "components": [
                    {
                        "id": "forged",
                        "category": "cabinet",
                        "label": "x",
                        "bbox": [0, 0, 1, 1],
                        "source": "grounding_dino",
                        "score": 0.99,
                    }
                ],
            },
        )
        assert response.status_code == 422
