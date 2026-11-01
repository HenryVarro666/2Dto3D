"""Independent test inputs must stay separate from tuning data and prior-run checks."""

import importlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image


def module(monkeypatch, name="independent_benchmark"):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3]/"scripts"))
    return importlib.import_module(name)


def test_independence_rejects_overlap_even_with_renamed_scene(monkeypatch):
    benchmark = module(monkeypatch)
    old = {"scenes": [{"id": "old", "views": [{"sha256": "same-photo"}]}]}
    fresh = {"scenes": [{"id": "new", "views": [{"sha256": "same-photo"}]}]}
    with pytest.raises(ValueError, match="PHOTO_OVERLAP"):
        benchmark.verify_independence(fresh, [old])
    fresh["scenes"][0].update(id="old", views=[{"sha256": "different"}])
    with pytest.raises(ValueError, match="SCENE_OVERLAP"):
        benchmark.verify_independence(fresh, [old])
    fresh["scenes"][0]["id"] = "new"
    benchmark.verify_independence(fresh, [old])


def test_fixed_mapping_uses_actual_scan_pixel_and_fractional_content(monkeypatch):
    benchmark = module(monkeypatch)
    from pv3d.metric_benchmark import camera_ray, photo_to_grid

    params = [400, 400, 300, 200, 0, 0, 0, 0, 0, 0, 0, 0]
    pixel = [210, 150]
    xyz = camera_ray(np.asarray(pixel)+.5, params)*2
    scene = {"camera": {"params": params, "size": [600, 400]},
             "fixed_points": [{"physical_xyz_m": xyz.tolist(), "source_pixel_xy": pixel}]}
    layout = {"mapping_rect": [0, 86.333333333, 518, 431.666666667], "rect": [0, 86, 518, 432]}
    mappings = benchmark.fixed_mappings(scene, "original", layout, np.ones((518, 518), bool))
    np.testing.assert_allclose(mappings[0]["grid_xy"], photo_to_grid(pixel, layout["mapping_rect"], [600, 400]), atol=1e-7)
    assert mappings[0]["physical_point_index"] == 0
    assert mappings[0]["roundtrip_residual_source_px"] < 1e-6
    assert len(mappings[0]["neighbours"]) == 4


def test_selected_camera_uses_image_id_instead_of_first_camera_row(tmp_path, monkeypatch):
    benchmark = module(monkeypatch)
    (tmp_path/"cameras.txt").write_text("1 THIN_PRISM_FISHEYE 600 400 " + " ".join(["9"]*12) +
                                      "\n0 THIN_PRISM_FISHEYE 600 400 " + " ".join(["4"]*12) + "\n")
    (tmp_path/"images.txt").write_text("1 1 0 0 0 0 0 0 0 dslr_images/one.JPG\n\n"
                                     "2 1 0 0 0 1 0 0 1 dslr_images/two.JPG\n\n")
    camera, ids, _ = benchmark.camera_for_views(tmp_path, ["one.JPG"])
    assert camera["id"] == 0 and camera["params"] == [4]*12 and ids == [0]
    with pytest.raises(ValueError, match="MIXED_SELECTED_CAMERAS"):
        benchmark.camera_for_views(tmp_path, ["one.JPG", "two.JPG"])


def test_publisher_rejects_missing_duplicate_and_moved_references(monkeypatch):
    publisher = module(monkeypatch, "publish_independent")
    protocol = {"model_revision": "model", "model_code_revision": "code", "scenes": [{
        "id": "scene", "cases": [{"image_condition": "original", "resize_mode": "isotropic",
                                 "input_tensor_sha256": "authored-tensor", "layout": {}}],
        "reference_lengths_mm": [100, 200, 300, 400, 500],
        "segments": [{"id": x} for x in ["AB", "CD", "EF", "GH", "IJ"]]}]}
    row = {"scene": "scene", "image_condition": "original", "resize_mode": "isotropic", "status": "succeeded",
           "input_size": 518, "view_count": 3, "reference_lengths_mm": [100, 200, 300, 400, 500],
           "calibration": {"known_length_mm": 100, "distance_units": 1, "mm_per_unit": 100}, "model": {"revision": "model", "code_revision": "code",
           "protocol_sha256": "frozen", "resize_mode": "isotropic", "image_condition": "original"},
           "input_tensor_sha256": "authored-tensor", "layout": {},
           "checks": [{"segment_id": x, "reference_mm": (i+2)*100, "calibrated_mm": (i+2)*100,
                       "relative_error_pct": 0, "absolute_error_mm": 0, "relative_distance_u": i+2} for i, x in enumerate(["CD", "EF", "GH", "IJ"])]}
    summary = {"protocol_sha256": "frozen", "runs": [row]}
    publisher.validate_round(summary, protocol, "frozen")
    for invalid in [[], [row, row]]:
        with pytest.raises(ValueError, match="CASE_SET"):
            publisher.validate_round({**summary, "runs": invalid}, protocol, "frozen")
    row["checks"][0]["reference_mm"] += .01
    with pytest.raises(ValueError, match="REFERENCE"):
        publisher.validate_round(summary, protocol, "frozen")


def test_independent_protocol_checks_inputs_without_e08_dependency(tmp_path, monkeypatch):
    benchmark = module(monkeypatch, "resize_benchmark")
    image = tmp_path/"image.png"
    Image.new("RGB", (32, 16), "red").save(image)
    mask = tmp_path/"support.npy"
    np.save(mask, np.ones((518, 518), bool), allow_pickle=False)
    case = {"inputs": [{"path": image.name, "file_sha256": benchmark.sha256(image)}],
            "support_mask": mask.name, "support_mask_sha256": benchmark.sha256(mask),
            "input_preview": image.name, "input_preview_sha256": benchmark.sha256(image),
            "resize_mode": "isotropic", "input_tensor_sha256": "tampered"}
    protocol = {"experiment_id": "E10-M", "configuration": benchmark.CONFIG, "scenes": [{"cases": [case]}]}
    with pytest.raises(ValueError, match="RESIZE_MODEL_TENSOR_CHANGED"):
        benchmark.verify_prepared(SimpleNamespace(image_dir=tmp_path, data_dir=tmp_path), protocol)


def test_independent_runner_keeps_failures_without_reading_e08_archive(tmp_path, monkeypatch):
    benchmark = module(monkeypatch, "resize_benchmark")
    monkeypatch.setattr(benchmark, "verify_prepared", lambda *_: None)
    monkeypatch.setattr(benchmark, "check_file", lambda *_: None)
    monkeypatch.setattr(benchmark, "ARCHIVE", tmp_path/"must-not-be-read.json")
    protocol_path = tmp_path/"protocol.json"
    protocol_path.write_text("{}")

    class Worker:
        def __init__(self, **_):
            pass

        def reconstruct(self, *_):
            raise RuntimeError("authored worker failure; no model call")

    monkeypatch.setattr(benchmark, "VggtReconstructor", Worker)
    args = SimpleNamespace(data_dir=tmp_path, runtime_dir=tmp_path/"runtime", runtime_root=tmp_path,
                           image_dir=tmp_path, run_name="failure", reverse_order=False,
                           image_conditions=["original"], resize_modes=["legacy14"], device="cpu",
                           protocol_path=protocol_path)
    case = {"image_condition": "original", "resize_mode": "legacy14", "inputs": [], "layout": {}}
    protocol = {"experiment_id": "E10-M", "scenes": [{"id": "new-scene", "cases": [case],
                                                       "reference_lengths_mm": [100]*5}]}
    with pytest.raises(SystemExit):
        benchmark.run(args, protocol)
    summary = json.loads((tmp_path/"runs/failure/summary.json").read_text())
    assert summary["experiment_id"] == "E10-M"
    assert summary["runs"][0]["status"] == "failed"
    assert "authored worker failure" in summary["runs"][0]["error"]


@pytest.mark.parametrize("tamper", ["stratum", "stratum_and_model", "tensor", "layout", "error",
                                    "absolute_error", "calibrated_length", "calibration_scale"])
def test_publication_binds_each_row_to_frozen_input_and_error_arithmetic(monkeypatch, tamper):
    publisher = module(monkeypatch, "publish_independent")
    cases = [{"image_condition": condition, "resize_mode": "legacy14", "input_tensor_sha256": condition+"-tensor",
              "layout": {"rect": [0, 84, 518, 434]}} for condition in ["original", "rectified"]]
    scene = {"id": "authored", "cases": cases, "reference_lengths_mm": [100, 200, 300, 400, 500],
             "segments": [{"id": v} for v in ["AB", "CD", "EF", "GH", "IJ"]]}
    protocol = {"model_revision": "model", "model_code_revision": "code", "scenes": [scene]}
    rows = []
    for case in cases:
        rows.append(deepcopy({**case, "scene": "authored", "status": "succeeded", "input_size": 518, "view_count": 3,
            "reference_lengths_mm": scene["reference_lengths_mm"], "calibration": {"known_length_mm": 100, "distance_units": 1, "mm_per_unit": 100},
            "model": {"revision": "model", "code_revision": "code", "protocol_sha256": "frozen",
                      "resize_mode": "legacy14", "image_condition": case["image_condition"]},
            "checks": [{"segment_id": v, "reference_mm": (i+2)*100, "calibrated_mm": (i+2)*100,
                        "relative_error_pct": 0, "absolute_error_mm": 0, "relative_distance_u": i+2} for i, v in enumerate(["CD", "EF", "GH", "IJ"])]}))
    summary = {"protocol_sha256": "frozen", "runs": rows}
    publisher.validate_round(summary, protocol, "frozen")
    if tamper.startswith("stratum"):
        rows[0]["image_condition"], rows[1]["image_condition"] = rows[1]["image_condition"], rows[0]["image_condition"]
        if tamper == "stratum_and_model":
            for row in rows:
                row["model"]["image_condition"] = row["image_condition"]
    elif tamper == "tensor":
        rows[0]["input_tensor_sha256"] = "another-preprocessing-policy"
    elif tamper == "layout":
        rows[0]["layout"]["rect"][1] += 1
    elif tamper == "error":
        rows[0]["checks"][0]["relative_error_pct"] = 999
    elif tamper == "absolute_error":
        rows[0]["checks"][0]["absolute_error_mm"] = 999
    elif tamper == "calibrated_length":
        rows[0]["checks"][0].update(calibrated_mm=400, absolute_error_mm=200, relative_error_pct=100)
    else:
        rows[0]["calibration"]["mm_per_unit"] *= 2
    with pytest.raises(ValueError, match="INDEPENDENT_(INPUT_CASE|INCONSISTENT_ERROR)"):
        publisher.validate_round(summary, protocol, "frozen")


@pytest.mark.parametrize("field", ["xyz_and_lengths", "depth_z_m", "sample_pixel_xy", "support_count",
                                    "depth_spread_m", "sample_shift_px", "selected_depth_deviation_m"])
def test_reference_verification_recomputes_scan_samples_instead_of_trusting_metadata(tmp_path, monkeypatch, field):
    benchmark = module(monkeypatch)
    from pv3d.metric_benchmark import reference_point

    base = tmp_path/"source-data/authored-independent"
    calibration = base/"dslr_calibration_jpg"
    calibration.mkdir(parents=True)
    params = [50, 50, 32, 24, *([0]*8)]
    (calibration/"cameras.txt").write_text("0 THIN_PRISM_FISHEYE 64 48 " + " ".join(map(str, params)) + "\n")
    (calibration/"images.txt").write_text("1 1 0 0 0 0 0 0 0 dslr_images/one.JPG\n\n")
    photo = base/"images/dslr_images/one.JPG"
    photo.parent.mkdir(parents=True)
    Image.new("RGB", (64, 48), "red").save(photo)
    depth = np.full((48, 64), 2, dtype="<f4")
    depth_path = base/"ground_truth_depth/dslr_images/one.JPG"
    depth_path.parent.mkdir(parents=True)
    depth.tofile(depth_path)
    points = [reference_point(depth, [20+i*2, 20], params) for i in range(10)]
    segments = [{"point_indices": [i, i+1]} for i in range(0, 10, 2)]
    lengths = [float(np.linalg.norm(np.asarray(points[i]["xyz_m"])-points[i+1]["xyz_m"])*1000)
               for i in range(0, 10, 2)]
    def file_row(p):
        return {"path": str(p.relative_to(tmp_path/"source-data")), "sha256": benchmark.sha256(p)}
    scene = {"id": "authored-independent", "camera": {"id": 0, "model": "THIN_PRISM_FISHEYE",
             "size": [64, 48], "params": params}, "selected_camera_ids": [0], "views": [file_row(photo)],
             "reference_files": [file_row(p) for p in [depth_path, calibration/"cameras.txt", calibration/"images.txt"]],
             "reference_points": points, "segments": segments, "reference_lengths_mm": lengths}
    source = {"scenes": [scene]}
    benchmark.verify_source_files(tmp_path, source)
    if field == "xyz_and_lengths":
        for p in points:
            p["xyz_m"] = (np.asarray(p["xyz_m"])*2).tolist()
        scene["reference_lengths_mm"] = [v*2 for v in lengths]
    elif field == "sample_pixel_xy":
        points[0][field][0] += 1
    else:
        points[0][field] += 1
    with pytest.raises(ValueError, match="INDEPENDENT_SCAN_REFERENCE_CHANGED"):
        benchmark.verify_source_files(tmp_path, source)


def test_new_metric_issue_ids_do_not_reuse_history_and_e09_receipts_stay_with_e09():
    text = (Path(__file__).resolve().parents[3]/"docs/quality/issues.md").read_text()
    history, new = text.split("## E10-M ", 1)
    new = new.split("\n## ", 1)[0]
    ids = [line.split("|")[1].strip() for line in new.splitlines()
           if line.startswith("|") and not line.startswith(("| ID", "|---"))]
    assert len(ids) == len(set(ids))
    for identifier in ids:
        assert f"| {identifier} |" not in history, f"Reused issue ID: {identifier}"
    e09 = history.split("## E09 ", 1)[1].split("\n## ", 1)[0]
    assert "本轮16真实调用" in e09
    assert "本轮16真实调用" not in new
