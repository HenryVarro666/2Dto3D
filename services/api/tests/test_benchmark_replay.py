import numpy as np
from PIL import Image
from pv3d.store import Store

from scripts.public_metric_benchmark import evaluate_api, seed_job


def fixture(tmp_path):
    paths = []
    for i in range(2):
        p = tmp_path / f"photo{i}.jpg"
        Image.new("RGB", (16, 16), (100+i, 140, 170)).save(p)
        paths.append(p)
    yy, xx = np.indices((16, 16))
    geometry = {"points": np.stack((xx, yy, np.ones_like(xx)), axis=-1)[None].repeat(2, axis=0),
                "depth": np.ones((2, 16, 16)), "colors": np.full((2, 16, 16, 3), 180, np.uint8),
                "rects": np.tile([0, 0, 16, 16], (2, 1))}
    points = [{"grid_xy": [x, y]} for y in [1, 3, 5, 7, 9] for x in [1, 3]]
    scene = {"id": "authored-test", "resolutions": {"16": {"points": points,
              "reference_lengths_mm": [2000]*5}}, "segments": [{"point_indices": [i*2, i*2+1],
              "id": str(i), "label": f"Authored test {i}"} for i in range(5)]}
    metadata = {"model": {"model_id": "authored-test-no-inference"}, "timings": {}}
    return paths, geometry, scene, metadata


def test_evaluation_does_not_interrupt_an_unrelated_queued_job(tmp_path):
    paths, geometry, scene, metadata = fixture(tmp_path)
    runtime = tmp_path / "runtime"
    job, indices, _ = seed_job(runtime, scene, paths, geometry, metadata, 16)
    store = Store(runtime)
    queued = store.create_multiview_job(store.get_multiview_job(job)["capture_id"], 2)
    evaluate_api(runtime, job, indices, scene, 16, geometry)
    assert store.get_multiview_job(queued["id"])["status"] == "queued"


def test_derived_anchors_have_separate_indices_raw_cloud_and_api_receipts(tmp_path):
    paths, geometry, scene, metadata = fixture(tmp_path)
    original = geometry["points"].copy()
    anchors = [[p["grid_xy"][0]+.25, p["grid_xy"][1]+.125, 1]
               for p in scene["resolutions"]["16"]["points"]]
    runtime = tmp_path / "runtime"
    job, indices, folder = seed_job(runtime, scene, paths, geometry, metadata, 16,
                                   measurement_points=anchors,
                                   support_masks=np.ones((2, 16, 16), bool))
    assert indices == list(range(10))
    assert (folder / "raw-cloud.glb").is_file()
    assert (folder / "raw-cloud.glb").read_bytes() != (folder / "cloud.glb").read_bytes()
    np.testing.assert_array_equal(geometry["points"], original)
    _, receipt = evaluate_api(runtime, job, indices, scene, 16, geometry,
                              point_component_id="measurement-anchors", expected_positions=anchors,
                              source_note="Authored fixed-position audit")
    assert len(receipt["calibrations"]) == 1
    assert receipt["calibrations"][0]["source_note"] == "Authored fixed-position audit"
    assert all(p["component_id"] == "measurement-anchors"
               for record in receipt["measurements"] for p in record["points"])
    np.testing.assert_allclose(receipt["calibrations"][0]["points"][0]["position"], [1.25, -1.125, -1])
