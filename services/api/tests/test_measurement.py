"""Metric receipts over actual exported points, without ML or field-accuracy claims."""
import hashlib
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pv3d.app import create_app
from pv3d.pointcloud import export_pointcloud
from pv3d.store import Store
from test_api import DetectorDouble


def seed_cloud(folder, *, stretch=1.0):
    store = Store(folder)
    capture = store.create_capture([])
    job = store.create_multiview_job(capture["id"], 2)
    output = folder / "multiview" / job["id"]
    output.mkdir()
    # A-B: 2 units, C-D: 3 units, E-F: 4 units. Duplicate coordinates retain indices.
    points = np.array([[0, 0, 0], [2, 0, 0], [0, 1, 0], [0, 1+3*stretch, 0],
                       [1, 0, 0], [1, 0, 4], [0, 0, 0], [2, 0, 0]], dtype=np.float32)
    export_pointcloud({"vertices": points, "colors": np.full((8, 3), 180, np.uint8),
                       "indices": np.ones(8, int), "components": [{"id": "part-a"}]}, output)
    store.update_multiview_job(job["id"], status="succeeded", result={
        "job_id": job["id"], "capture_id": capture["id"], "geometry_job_id": job["id"],
        "representation": "fused_point_cloud", "metric_scale_status": "unknown",
        "scene_url": f"/api/multiview/jobs/{job['id']}/cloud.glb",
        "components": [{"id": "part-a"}], "model": {"model_id": "authored-analytic-fixture"}})
    return job["id"], output


def point(index, component="part-a"):
    return {"component_id": component, "point_index": index}


def segment(a=0, b=1):
    return [point(a), point(b)]


def calibration(client, base, fingerprint):
    r = client.post(base + "/calibrations", json={"geometry_sha256": fingerprint,
        "points": segment(), "known_length": 20, "unit": "cm", "label": "Width A–B",
        "source_note": "Authored fixture: reference 200 mm; not a field measurement."})
    assert r.status_code == 201, r.text
    return r.json()


def test_relative_calibrated_and_independent_errors_persist_without_scaling_raw_glb(tmp_path):
    job_id, folder = seed_cloud(tmp_path, stretch=1.1)
    base = f"/api/multiview/jobs/{job_id}/measurements"
    raw = (folder / "cloud.glb").read_bytes()
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        session = client.get(base)
        assert session.status_code == 200, session.text
        session = session.json()
        fingerprint = session["geometry_sha256"]
        assert fingerprint == hashlib.sha256(raw).hexdigest()
        assert session["calibrations"] == [] and session["measurements"] == []
        request = {"geometry_sha256": fingerprint, "points": segment(2, 3), "label": "Height"}
        estimated = client.post(base, json=request).json()
        assert estimated["scale_status"] == "relative_estimate"
        assert estimated["distance_units"] == pytest.approx(3.3)
        assert estimated["distance_mm"] is None
        cal = calibration(client, base, fingerprint)
        assert cal["mm_per_unit"] == pytest.approx(100)
        measured = client.post(base, json={**request, "calibration_id": cal["id"],
            "validation": {"known_length": 0.3, "unit": "m", "source_note": "Independent authored height"}})
        assert measured.status_code == 201, measured.text
        measured = measured.json()
        assert measured["scale_status"] == "reference_calibrated"
        assert measured["distance_mm"] == pytest.approx(330)
        assert measured["validation"]["absolute_error_mm"] == pytest.approx(30)
        assert measured["validation"]["relative_error_pct"] == pytest.approx(10)
        assert measured["points"][0]["position"] == [0, 1, 0]
        assert measured["calibration_id"] == cal["id"]
        exported = client.get(base + "/export.json")
        assert exported.status_code == 200 and "attachment" in exported.headers["content-disposition"]
        saved = exported.json()
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        assert client.get(base).json() == saved
    assert (folder / "cloud.glb").read_bytes() == raw
    assert Store(tmp_path).get_multiview_job(job_id)["result"]["metric_scale_status"] == "unknown"


def test_rejects_reference_as_heldout_including_reversed_and_duplicate_coordinate_indices(tmp_path):
    job_id, _ = seed_cloud(tmp_path)
    base = f"/api/multiview/jobs/{job_id}/measurements"
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        fingerprint = client.get(base).json()["geometry_sha256"]
        cal = calibration(client, base, fingerprint)
        for points in [segment(), segment(1, 0), segment(6, 7), segment(7, 6)]:
            r = client.post(base, json={"geometry_sha256": fingerprint, "points": points,
                "calibration_id": cal["id"], "validation": {
                    "known_length": 200, "unit": "mm", "source_note": "Should not count as independent"}})
            assert r.status_code == 422, r.text
            assert r.json()["detail"] == "MEASUREMENT_REFERENCE_REUSED"
        # Re-measuring the reference is allowed, but can never count as validation.
        assert client.post(base, json={"geometry_sha256": fingerprint, "points": segment(),
                                      "calibration_id": cal["id"]}).status_code == 201


def test_validates_indices_units_known_lengths_and_does_not_trust_client_coordinates(tmp_path):
    job_id, _ = seed_cloud(tmp_path)
    base = f"/api/multiview/jobs/{job_id}/measurements"
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        sha = client.get(base).json()["geometry_sha256"]
        good = {"geometry_sha256": sha, "points": segment(), "known_length": 200,
                "unit": "mm", "source_note": "authored analytic reference"}
        for patch in [{"known_length": 0}, {"known_length": -1}, {"known_length": 1e308},
                      {"unit": "inch"}, {"source_note": " "}, {"points": segment(0, 6)},
                      {"points": segment(0, 0)}, {"points": segment(-1, 2)},
                      {"points": segment(0, 8)}, {"points": [point(0, "unknown"), point(1)]},
                      {"points": [{**point(0), "position": [0, 0, 0]}, point(1)]}]:
            r = client.post(base + "/calibrations", json={**good, **patch})
            assert r.status_code == 422, (patch, r.text)
        for value in ["NaN", "Infinity", "-Infinity"]:
            body = json.dumps(good).replace('200', value)
            assert client.post(base + "/calibrations", content=body,
                               headers={"Content-Type": "application/json"}).status_code == 422
        assert client.get("/api/multiview/jobs/not-valid/measurements").status_code == 404
        assert client.post(base, json={"geometry_sha256": sha, "points": segment(2, 3),
            "validation": {"known_length": 300, "unit": "mm", "source_note": "held out"}}).status_code == 422


def test_geometry_and_job_ownership_and_immutable_calibration_history(tmp_path):
    job, output = seed_cloud(tmp_path)
    other, _ = seed_cloud(tmp_path)
    base = f"/api/multiview/jobs/{job}/measurements"
    second = f"/api/multiview/jobs/{other}/measurements"
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        sha = client.get(base).json()["geometry_sha256"]
        cal1 = calibration(client, base, sha)
        cal2 = calibration(client, base, sha)
        assert cal1["id"] != cal2["id"]
        assert len(client.get(base).json()["calibrations"]) == 2
        r = client.post(second, json={"geometry_sha256": client.get(second).json()["geometry_sha256"],
                                     "points": segment(2, 3), "calibration_id": cal1["id"]})
        assert r.status_code == 422
        # A modified asset (even valid GLB plus trailing bytes) must not reuse the old receipt.
        with (output / "cloud.glb").open("ab") as stream:
            stream.write(b"changed")
        r = client.post(base, json={"geometry_sha256": sha, "points": segment(2, 3),
                                  "calibration_id": cal1["id"]})
        assert r.status_code == 409


def test_point_order_and_context_use_glb_world_coordinates(tmp_path):
    import trimesh

    job, output = seed_cloud(tmp_path)
    scene = trimesh.Scene(base_frame="scene-root")
    transform = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1])
    transform[:3, 3] = [10, 20, 30]
    cloud = trimesh.points.PointCloud([[0, 0, 0], [2, 0, 0], [0, 0, 0]])
    scene.add_geometry(cloud, node_name="part-a", geom_name="part-a", transform=transform)
    scene.add_geometry(trimesh.points.PointCloud([[10, 20, 34]]), node_name="__context__", geom_name="__context__")
    (output / "cloud.glb").write_bytes(trimesh.exchange.gltf.export_glb(scene))
    base = f"/api/multiview/jobs/{job}/measurements"
    with TestClient(create_app(tmp_path, DetectorDouble())) as client:
        sha = client.get(base).json()["geometry_sha256"]
        r = client.post(base, json={"geometry_sha256": sha, "points": [point(1), point(0, "__context__")]})
        assert r.status_code == 201, r.text
        record = r.json()
        assert record["points"][0]["position"] == pytest.approx([10, 22, 30])
        assert record["points"][1]["position"] == [10, 20, 34]
        assert record["distance_units"] == pytest.approx(np.sqrt(20))
        assert client.post(base, json={"geometry_sha256": sha, "points": segment(0, 2)}).status_code == 422
