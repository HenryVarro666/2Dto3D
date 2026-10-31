"""Capture ownership and job boundaries, without downloading model weights."""

import json
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pv3d.app import create_app
from test_api import DetectorDouble, picture, upload


class GeometryBoundary:
    calls = 0

    def status(self):
        return {"state": "available"}

    def reconstruct(self, image_paths, folder, on_progress):
        from test_pointcloud import geometry

        self.calls += 1
        on_progress("estimating_geometry")
        np.savez_compressed(folder / "geometry.npz", **geometry())
        meta = {"model": {"model_id": "analytic-test-boundary"}, "timings": {}}
        (folder / "geometry.json").write_text(json.dumps(meta))
        return meta


def pair(client):
    return [upload(client), upload(client, picture((321, 200)))]


def capture(client, assets=None):
    assets = assets or pair(client)
    response = client.post("/api/captures", json={"asset_ids": [a["id"] for a in assets]})
    assert response.status_code == 201, response.text
    return response.json()


def multi_terminal(client, identifier):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = client.get(f"/api/multiview/jobs/{identifier}").json()
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.01)
    pytest.fail("multiview job did not finish")


def test_capture_persists_ordered_unique_photos_and_keeps_v2_assets(tmp_path):
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        assets = pair(client)
        group = capture(client, assets)
        assert [a["id"] for a in group["assets"]] == [a["id"] for a in assets]
        assert client.get(f"/api/captures/{group['id']}").json() == group
        assert client.get(assets[0]["image_url"]).status_code == 200
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        assert client.get(f"/api/captures/{group['id']}").json() == group


def test_capture_rejects_missing_duplicate_or_reencoded_same_input_references(tmp_path):
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        a, b = pair(client)
        same = upload(client)  # A new asset ID holding the exact same photo bytes.
        for ids, status in [
            ([a["id"]], 422),
            ([a["id"]] * 9, 422),
            ([a["id"], a["id"]], 422),
            ([a["id"], "0" * 32], 404),
            ([a["id"], same["id"]], 400),
        ]:
            response = client.post("/api/captures", json={"asset_ids": ids})
            assert response.status_code == status, response.text
        assert client.post("/api/captures", json={"asset_ids": [a["id"], b["id"]]}).status_code == 201


def test_multiview_modes_and_manual_references_are_validated_before_queueing(tmp_path):
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        group = capture(client)
        unknown_asset = upload(client, picture((322, 200)))
        base = {"capture_id": group["id"]}
        observation = {
            "id": "obs-a",
            "asset_id": unknown_asset["id"],
            "label": "Cable",
            "category": "cables",
            "bbox": [0.1, 0.1, 0.5, 0.9],
        }
        for payload, status in [
            ({**base, "mode": "wrong"}, 422),
            ({**base, "observations": []}, 422),
            ({**base, "mode": "manual", "observations": []}, 422),
            ({**base, "mode": "manual", "observations": [observation], "base_job_id": "0" * 32}, 400),
        ]:
            response = client.post("/api/multiview/jobs", json=payload)
            assert response.status_code == status, response.text
        assert client.get("/api/multiview/jobs/not-an-id").status_code == 404
        assert client.get("/api/captures/not-an-id").status_code == 404


def test_multiview_jobs_share_the_existing_bounded_inference_queue(tmp_path):
    app = create_app(tmp_path, DetectorDouble())
    with TestClient(app) as client:
        group = capture(client)
        capacity = app.state.runner.capacity
        for _ in range(8):
            assert capacity.acquire(blocking=False)
        try:
            assert client.post("/api/multiview/jobs", json={"capture_id": group["id"]}).status_code == 409
            assert client.post("/api/jobs", json={"asset_id": group["assets"][0]["id"]}).status_code == 409
        finally:
            for _ in range(8):
                capacity.release()


def test_new_multiview_job_is_durable_and_restart_interrupts_it(tmp_path):
    from pv3d.store import Store

    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        group = capture(client)
        store = Store(tmp_path)
        job = store.create_multiview_job(group["id"], 2)
        store.update_multiview_job(job["id"], status="running", stage="estimating_geometry")
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        response = client.get(f"/api/multiview/jobs/{job['id']}")
        assert response.status_code == 200
        restored = response.json()
        assert restored["status"] == "interrupted" and restored["result"] is None
        assert restored["total_views"] == 2
        assert client.get(f"/api/multiview/jobs/{job['id']}/result.json").status_code == 409
        assert str(tmp_path) not in json.dumps(restored)


def test_manual_capture_rejects_cross_group_base_and_cross_photo_refinement(tmp_path):
    from pv3d.store import Store
    from test_refinement import RefinerDouble

    with TestClient(create_app(tmp_path, RefinerDouble())) as client:
        group = capture(client)
        second = capture(client, [group["assets"][0], upload(client, picture((322, 200)))])
        store = Store(tmp_path)
        old = store.create_multiview_job(group["id"], 2)
        store.update_multiview_job(old["id"], status="succeeded", result={"capture_id": group["id"]})
        request = {"capture_id": second["id"], "mode": "manual", "observations": [], "base_job_id": old["id"]}
        assert client.post("/api/multiview/jobs", json=request).status_code == 400
        asset = group["assets"][0]
        ref = client.post(
            "/api/refinements", json={"asset_id": asset["id"], "bbox": [0.1, 0.05, 0.8, 0.9]}
        ).json()
        for asset_id, box in [
            (group["assets"][1]["id"], ref["geometry_bbox"]),
            (asset["id"], [0.1, 0.1, 0.9, 0.9]),
        ]:
            observation = {
                "id": "obs-ref",
                "asset_id": asset_id,
                "category": "cables",
                "label": "Cables",
                "bbox": box,
                "refinement_id": ref["id"],
            }
            response = client.post(
                "/api/multiview/jobs",
                json={**request, "capture_id": group["id"], "observations": [observation]},
            )
            assert response.status_code == 400, response.text


def test_real_job_fusion_artifacts_and_manual_reuse_preserve_observation_identity(tmp_path):
    model = GeometryBoundary()
    detector = DetectorDouble([{"category": "cabinet", "label": "Cabinet", "bbox": [0.1, 0.2, 0.6, 0.8],
                                "score": 0.8, "source": "grounding_dino"}])
    with TestClient(create_app(tmp_path, detector, reconstructor=model)) as client:
        group = capture(client)
        queued = client.post("/api/multiview/jobs", json={"capture_id": group["id"]}).json()
        job = multi_terminal(client, queued["id"])
        assert job["status"] == "succeeded", job
        result = job["result"]
        assert result["point_count"] > 0 and len(result["observations"]) == 2
        assert result["geometry_job_id"] == job["id"]
        assert client.get(result["scene_url"]).content[:4] == b"glTF"
        assert client.get(result["ply_url"]).content[:3] == b"ply"
        assert client.get(result["json_url"]).json() == result
        observations = [{k: o[k] for k in ("id", "asset_id", "category", "label", "bbox", "component_id")}
                        for o in result["observations"]]
        request = {"capture_id": group["id"], "mode": "manual", "base_job_id": job["id"],
                   "observations": observations}
        # Reusing an observation ID on another view must not inherit the first view's mask evidence.
        bad = [{**observations[0], "asset_id": group["assets"][1]["id"]}]
        assert client.post("/api/multiview/jobs", json={**request, "observations": bad}).status_code == 400
        for o in observations:
            o.update(label="Confirmed housing", category="unknown", component_id="part-confirmed")
        response = client.post("/api/multiview/jobs", json=request)
        assert response.status_code == 202, response.text
        edited = multi_terminal(client, response.json()["id"])["result"]
        assert model.calls == 1
        assert edited["geometry_job_id"] == job["id"]
        assert edited["model"]["geometry_reused"] is True
        assert edited["timings"]["geometry_ms"] == 0
        assert edited["components"][0]["id"] == "part-confirmed"
        assert edited["components"][0]["label"] == "Confirmed housing"
        assert {o["id"] for o in edited["observations"]} == {o["id"] for o in observations}
        observations[1]["label"] = "Conflicting label"
        assert client.post("/api/multiview/jobs", json=request).status_code == 400
        # Omitted IDs inherit the base grouping, so its linked semantics still need validation.
        inherited = [{k: o[k] for k in ("id", "asset_id", "category", "label", "bbox")}
                     for o in result["observations"]]
        inherited[1]["label"] = "Contradictory inherited name"
        assert client.post("/api/multiview/jobs", json={**request, "observations": inherited}).status_code == 400


def test_model_failure_is_sanitized_and_retains_capture_for_retry(tmp_path):
    class BrokenGeometry(GeometryBoundary):
        def reconstruct(self, *args):
            raise RuntimeError(f"private path: {tmp_path}")

    with TestClient(create_app(tmp_path, DetectorDouble(), reconstructor=BrokenGeometry())) as client:
        group = capture(client)
        queued = client.post("/api/multiview/jobs", json={"capture_id": group["id"]}).json()
        job = multi_terminal(client, queued["id"])
        assert job["status"] == "failed" and job["result"] is None
        assert str(tmp_path) not in json.dumps(job)
        assert client.get(f"/api/captures/{group['id']}").json() == group
