#!/usr/bin/env python3
"""E08: fixed physical endpoints, original vs calibrated-rectified RGB at518px."""

import argparse
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
from httpx import HTTPError
from PIL import Image
from PIL import __version__ as pillow_version
from public_metric_benchmark import (
    check_file,
    download_sources,
    evaluate_api,
    seed_job,
    sha256,
    verify_sources,
    write_json,
)
from pv3d.metric_benchmark import camera_project, camera_ray, photo_to_grid
from pv3d.reconstruction import (
    VGGT_CODE_REVISION,
    VGGT_REVISION,
    VggtReconstructor,
    load_geometry,
    prepare_images,
)
from pv3d.undistortion import (
    bilinear_footprint,
    full_field_camera,
    grid_camera_matrix,
    model_support_mask,
    pinhole_to_source,
    project_pinhole,
    rectify_rgb,
    sample_camera_depth,
    unproject_depth,
)

ROOT = Path(__file__).resolve().parents[1]
E07 = ROOT / "docs/measurement/public-metric-selection.json"
PROTOCOL = ROOT / "docs/measurement/undistortion-selection.json"
CONFIG = {"input_size": 518, "boundary_samples_per_edge": 257, "boundary_validation_per_edge": 1025,
          "full_field_margin_fraction": .002, "remap": "OpenCV INTER_LINEAR; white BORDER_CONSTANT",
          "resize": "unchanged PIL BICUBIC/14-aligned letterbox",
          "support": "erode source validity by ceil(2*max_downscale)+2px before grid lookup",
          "sampling": "bilinear camera-Z then predicted-K/extrinsic unprojection; no pixel snapping",
          "auxiliary_known_K": "rectified only; separate A-B-only diagnostic scale; not primary metric"}


def array_sha(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def save_lossless(path, rgb):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with Image.open(path) as old:
            if not np.array_equal(np.array(old.convert("RGB")), rgb):
                raise ValueError(f"Immutable prepared pixels changed: {path}")
    else:
        Image.fromarray(rgb).save(path, format="PNG", compress_level=6)


def boundary_projection_margin(params, size, k):
    width, height = size
    xs = np.linspace(.5, width-.5, CONFIG["boundary_validation_per_edge"])
    ys = np.linspace(.5, height-.5, CONFIG["boundary_validation_per_edge"])
    boundary = ([(x, y) for y in [.5, height-.5] for x in xs]
                + [(x, y) for x in [.5, width-.5] for y in ys])
    positions = project_pinhole(np.array([camera_ray(p, params) for p in boundary]), k)
    margin = float(np.min(np.minimum(positions, np.asarray(size)-1-positions)))
    if margin < -1e-6:
        raise ValueError("RECTIFICATION_CROPS_VALID_SOURCE_BOUNDARY")
    return margin


def prepare(source_root, data_root, freeze):
    source = json.loads(E07.read_text())
    verify_sources(source_root, source)
    cv2.setNumThreads(4)
    protocol = {"schema_version": 1, "experiment_id": "E08",
        "created_at": datetime.now(UTC).isoformat(), "inference_started_at_freeze": False,
        "baseline_commit": "8253f36", "source_e07_selection_sha256": sha256(E07),
        "model_revision": VGGT_REVISION, "model_code_revision": VGGT_CODE_REVISION,
        "configuration": CONFIG, "versions": {"numpy": np.__version__, "opencv": cv2.__version__,
                                                "pillow": pillow_version}, "scenes": []}
    preparation_times = []
    for original in source["scenes"]:
        started = time.perf_counter()
        name, camera = original["id"], original["camera"]
        size, params = camera["size"], camera["params"]
        k = full_field_camera(params, size, samples=CONFIG["boundary_samples_per_edge"],
                              margin=CONFIG["full_field_margin_fraction"])
        boundary_margin = boundary_projection_margin(params, size, k)
        ref = original["resolutions"]["518"]
        fixed = [{"physical_xyz_m": p["xyz_m"], "source_pixel_xy": p["sample_pixel_xy"],
                  "source_depth_z_m": p["depth_z_m"]} for p in ref["points"]]
        scene = {"id": name, "source_views": original["views"], "camera": camera,
                 "fixed_points": fixed, "segments": original["segments"],
                 "reference_lengths_mm": ref["reference_lengths_mm"],
                 "rectified_camera_K_colmap": k.tolist(),
                 "source_boundary_min_margin_px": boundary_margin, "conditions": {}}
        # The supplied calibration has one camera; verify every selected image uses it.
        camera_ids = {}
        calibration = source_root/"source-data"/name/"dslr_calibration_jpg/images.txt"
        for line in calibration.read_text().splitlines():
            words = line.split()
            if len(words) == 10 and words[-1].lower().endswith(".jpg"):
                camera_ids[Path(words[-1]).name] = int(words[8])
        assert all(camera_ids[Path(v["path"]).name] == 0 for v in original["views"])
        scene["selected_camera_ids"] = [0]*3
        for condition in ["original", "rectified"]:
            paths, inputs, full_valid = [], [], None
            warp_ms = 0.0
            for view in original["views"]:
                original_path = source_root/"source-data"/view["path"]
                with Image.open(original_path) as image:
                    rgb = np.asarray(image.convert("RGB"))
                if condition == "rectified":
                    begin = time.perf_counter()
                    rgb, valid = rectify_rgb(rgb, params, k)
                    warp_ms += (time.perf_counter()-begin)*1000
                else:
                    valid = np.ones(rgb.shape[:2], bool)
                if full_valid is None:
                    full_valid = valid
                else:
                    np.testing.assert_array_equal(valid, full_valid)
                path = data_root/"inputs"/name/condition/(original_path.stem+".png")
                save_lossless(path, rgb)
                inputs.append({"path": str(path.relative_to(data_root)), "file_sha256": sha256(path),
                               "rgb_sha256": array_sha(rgb), "original_jpeg_sha256": view["sha256"]})
                paths.append(path)
            tensors, rects = prepare_images(paths, 518)
            mask = model_support_mask(full_valid, rects[0], 518)
            mask_path = data_root/"inputs"/name/condition/"model-support.npy"
            np.save(mask_path, mask, allow_pickle=False)
            Image.fromarray(full_valid.astype(np.uint8)*255).save(mask_path.with_name("photo-valid.png"))
            mappings = []
            for index, point in enumerate(fixed):
                xyz = np.asarray(point["physical_xyz_m"])
                original_pixel = camera_project(xyz[:2]/xyz[2], params)-.5
                np.testing.assert_allclose(original_pixel, point["source_pixel_xy"], atol=1e-6, rtol=0)
                pixel = original_pixel if condition == "original" else project_pinhole(xyz, k)
                recovered = pixel if condition == "original" else pinhole_to_source(pixel, params, k)
                residual = float(np.linalg.norm(recovered-original_pixel))
                if residual > 1e-6:
                    raise ValueError("FIXED_PHYSICAL_POINT_MAPPING_CHANGED")
                grid = photo_to_grid(pixel, rects[0], size)
                neighbours, weights = bilinear_footprint(grid, rects[0], mask)
                mappings.append({"physical_point_index": index, "photo_xy": pixel.tolist(), "grid_xy": grid,
                    "roundtrip_residual_source_px": residual,
                    "neighbours": [{"xy": list(map(int, p)), "weight": float(w)}
                                   for p, w in zip(neighbours, weights, strict=True)]})
            scene["conditions"][condition] = {"inputs": inputs, "rect": rects[0].tolist(),
                "input_tensor_sha256": array_sha(tensors), "point_mappings": mappings,
                "support_mask": str(mask_path.relative_to(data_root)), "support_mask_sha256": sha256(mask_path),
                "photo_invalid_fraction": float(1-full_valid.mean()),
                "model_valid_pixel_count": int(mask.sum())}
            preparation_times.append({"scene": name, "condition": condition, "warp_rgb_ms": warp_ms})
            if condition == "original":
                old_paths = [source_root/"source-data"/v["path"] for v in original["views"]]
                old_tensor, _ = prepare_images(old_paths, 518)
                np.testing.assert_array_equal(tensors, old_tensor)
                scene["original_tensor_matches_e07_jpeg"] = True
        for j, segment in enumerate(scene["segments"]):
            a, b = [np.asarray(fixed[i]["physical_xyz_m"]) for i in segment["point_indices"]]
            np.testing.assert_allclose(np.linalg.norm(a-b)*1000, scene["reference_lengths_mm"][j], atol=1e-9)
        protocol["scenes"].append(scene)
        print(f"Prepared {name}: boundary margin {boundary_margin:.3f}px; "
              f"invalid border {scene['conditions']['rectified']['photo_invalid_fraction']:.3%}; "
              f"elapsed {time.perf_counter()-started:.1f}s", flush=True)
    if freeze:
        if PROTOCOL.exists():
            raise ValueError("Protocol already frozen; never overwrite it")
        write_json(PROTOCOL, protocol)
    else:
        expected = json.loads(PROTOCOL.read_text())
        for key in ["model_revision", "model_code_revision", "source_e07_selection_sha256", "configuration", "scenes"]:
            if expected[key] != protocol[key]:
                raise ValueError(f"Frozen preprocessing differs: {key}; preserve as a separate experiment")
    write_json(data_root/"preparation.json", {"protocol_sha256": sha256(PROTOCOL),
        "actual_versions": protocol["versions"], "timings": preparation_times})
    print(f"Protocol verified/frozen: {sha256(PROTOCOL)}", flush=True)


def verify_prepared(data_root, protocol):
    for scene in protocol["scenes"]:
        for condition in scene["conditions"].values():
            for item in condition["inputs"]:
                check_file(data_root/item["path"], item["file_sha256"])
            check_file(data_root/condition["support_mask"], condition["support_mask_sha256"])
            tensor, _ = prepare_images([data_root/p["path"] for p in condition["inputs"]], 518)
            if array_sha(tensor) != condition["input_tensor_sha256"]:
                raise ValueError("PREPARED_MODEL_TENSOR_CHANGED")


def point_diagnostics(scene, condition, samples, geometry, scale):
    reference = scene["reference_lengths_mm"]
    pair_ids = [s["point_indices"] for s in scene["segments"]]
    primary = np.array([s["world_xyz"] for s in samples]).astype(np.float32).astype(float)
    primary_lengths = [float(np.linalg.norm(primary[a]-primary[b])) for a, b in pair_ids]
    rows, max_raw_difference, variant_points = [], 0.0, []
    for i, sample in enumerate(samples):
        variant = np.zeros(3)
        for neighbour in sample["neighbours"]:
            x, y = neighbour["x"], neighbour["y"]
            raw = geometry["points"][0, y, x]
            _, reconstructed = unproject_depth([x, y], neighbour["depth_z"],
                geometry["intrinsics"][0], geometry["extrinsics"][0])
            np.testing.assert_allclose(raw, reconstructed, atol=1e-5, rtol=1e-5)
            max_raw_difference = max(max_raw_difference, float(np.max(np.abs(raw-reconstructed))))
            variant += neighbour["weight"]*raw
        variant_points.append(variant)
        true_z_mm = scene["fixed_points"][i]["source_depth_z_m"]*1000
        predicted_z_mm = sample["depth_z"]*scale
        rows.append({"point_index": i, "true_camera_z_mm": true_z_mm,
            "primary_scale_camera_z_mm": predicted_z_mm,
            "primary_scale_camera_z_signed_error_pct": (predicted_z_mm/true_z_mm-1)*100,
            "relative_neighbour_depth_spread": sample["relative_neighbour_depth_spread"],
            "pointmap_vs_depth_interpolation_delta_mm": float(np.linalg.norm(variant-primary[i])*scale)})
    out = {"primary_mm_per_unit": scale, "camera_z_scope": "conditional on primary scale and model camera; not causal proof",
        "predicted_camera_K_grid": geometry["intrinsics"][0].tolist(), "points": rows,
        "integer_unprojection_max_abs_raw_units": max_raw_difference,
        "raw_length_ratios_to_reference": [v/primary_lengths[0] for v in primary_lengths],
        "true_length_ratios_to_reference": [v/reference[0] for v in reference]}
    variant_points = np.array(variant_points)
    out["pointmap_interpolation_check_lengths_mm_same_primary_scale"] = [
        float(np.linalg.norm(variant_points[a]-variant_points[b])*scale) for a, b in pair_ids]
    if condition == "rectified":
        rect = scene["conditions"][condition]["rect"]
        k = grid_camera_matrix(scene["rectified_camera_K_colmap"], rect, scene["camera"]["size"])
        points = np.array([unproject_depth(s["grid_xy"], s["depth_z"], k, geometry["extrinsics"][0])[1]
                           for s in samples])
        lengths = [float(np.linalg.norm(points[a]-points[b])) for a, b in pair_ids]
        auxiliary_scale = reference[0]/lengths[0]
        out["known_K_auxiliary"] = {"scope": "separate A-B-only diagnostic scale; not primary before/after metric",
            "K_grid": k.tolist(), "mm_per_unit": auxiliary_scale,
            "checks": [{"segment_id": scene["segments"][i]["id"],
                        "calibrated_mm": lengths[i]*auxiliary_scale,
                        "relative_error_pct": abs(lengths[i]*auxiliary_scale/reference[i]-1)*100}
                       for i in range(1, 5)]}
    return out


def run(args, protocol):
    data_root, runtime = args.data_dir.resolve(), args.runtime_dir.resolve()
    verify_prepared(data_root, protocol)
    folder = data_root/"runs"/args.run_name
    if (folder/"summary.json").exists():
        raise ValueError("Frozen run exists; choose another --run-name")
    folder.mkdir(parents=True, exist_ok=True)
    runtime_root = args.runtime_root.resolve()
    weights = runtime_root/"models/huggingface/models--facebook--VGGT-1B/snapshots"/VGGT_REVISION/"model.safetensors"
    check_file(weights, "f164acf60724910d8fe1578bb499d800850c7bb0948db7555c413f9fbe60467e")
    summary = {"schema_version": 1, "experiment_id": "E08", "created_at": datetime.now(UTC).isoformat(),
        "protocol_sha256": sha256(PROTOCOL), "input_size": 518,
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "code_file_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in [Path(__file__).resolve(),
            ROOT/"services/api/src/pv3d/undistortion.py", ROOT/"services/multiview/infer.py"]},
        "conditions_order": args.conditions, "configuration": CONFIG, "runs": []}
    for condition in args.conditions:
        for scene in protocol["scenes"]:
            selected = scene["conditions"][condition]
            paths = [data_root/p["path"] for p in selected["inputs"]]
            destination = folder/f"{scene['id']}-{condition}"
            row = {"scene": scene["id"], "condition": condition, "input_size": 518, "view_count": 3,
                   "reference_lengths_mm": scene["reference_lengths_mm"], "status": "running"}
            summary["runs"].append(row); write_json(folder/"summary.json", summary)
            started = time.perf_counter()
            try:
                worker = VggtReconstructor(runtime_python=runtime_root/"services/multiview/.venv/bin/python",
                    worker_script=ROOT/"services/multiview/infer.py", cache_dir=runtime_root/"models/huggingface",
                    device=args.device, input_size=518)
                metadata = worker.reconstruct(paths, destination,
                    lambda stage, label=f"{scene['id']}/{condition}": print(f"{label}: {stage}", flush=True))
                row["worker_wall_ms"] = (time.perf_counter()-started)*1000
                assert metadata["input_tensor_sha256"] == selected["input_tensor_sha256"]
                assert metadata["model"]["revision"] == protocol["model_revision"]
                geometry = load_geometry(destination/"geometry.npz", 3)
                assert all(r.tolist() == selected["rect"] for r in geometry["rects"])
                mask = np.load(data_root/selected["support_mask"], allow_pickle=False)
                samples = [sample_camera_depth(geometry, p["grid_xy"], mask)
                           for p in selected["point_mappings"]]
                for a, b in zip(samples, selected["point_mappings"], strict=True):
                    assert [(p["x"], p["y"]) for p in a["neighbours"]] == [tuple(p["xy"]) for p in b["neighbours"]]
                    np.testing.assert_allclose([p["weight"] for p in a["neighbours"]],
                                               [p["weight"] for p in b["neighbours"]], atol=1e-12, rtol=0)
                write_json(destination/"derived-anchor-audit.json", samples)
                points = [s["world_xyz"] for s in samples]
                eval_scene = {**scene, "resolutions": {"518": {"points": selected["point_mappings"],
                    "reference_lengths_mm": scene["reference_lengths_mm"]}}}
                metadata["model"].update(experiment_id="E08", image_condition=condition,
                    measurement_sampling=CONFIG["sampling"], protocol_sha256=sha256(PROTOCOL))
                job, indices, job_folder = seed_job(runtime, eval_scene, paths, geometry, metadata, 518,
                    measurement_points=points, support_masks=np.tile(mask, (3, 1, 1)))
                measured, receipt = evaluate_api(runtime, job, indices, eval_scene, 518, geometry,
                    point_component_id="measurement-anchors", expected_positions=points,
                    source_note=f"E08 ETH3D {scene['id']}/{condition}; identical physical scanner points; "
                                "derived bilinear camera-Z anchors, predicted camera; reference depth not given to VGGT.")
                write_json(destination/"receipt.json", receipt)
                diagnostics = point_diagnostics(scene, condition, samples, geometry, measured["calibration"]["mm_per_unit"])
                write_json(destination/"diagnostics.json", diagnostics)
                row.update(status="succeeded", model=metadata["model"], input_tensor_sha256=metadata["input_tensor_sha256"],
                    model_timings=metadata["timings"], **measured, diagnostics=diagnostics,
                    raw_cloud_sha256=sha256(job_folder/"raw-cloud.glb"))
                if condition == "original":
                    old_path = args.source_dir.resolve()/"runs/2026-11-01-vggt-metric"/f"{scene['id']}-518/geometry.npz"
                    if old_path.exists():
                        old = load_geometry(old_path, 3)
                        row["model_arrays_equal_e07"] = all(np.array_equal(v, old[k]) for k, v in geometry.items())
                        assert row["model_arrays_equal_e07"]
                print(f"{scene['id']}/{condition} errors%: " + str([
                    round(c["relative_error_pct"], 3) for c in row["checks"]]), flush=True)
            except (OSError, ValueError, RuntimeError, AssertionError, HTTPError) as error:
                row.update(status="failed", error=f"{type(error).__name__}: {error}",
                           failed_wall_ms=(time.perf_counter()-started)*1000)
                print(row["error"], flush=True)
            write_json(folder/"summary.json", summary)
    print(f"Summary: {folder/'summary.json'}", flush=True)
    failed = [row for row in summary["runs"] if row["status"] != "succeeded"]
    if failed:
        raise SystemExit(f"E08: {len(failed)} case(s) failed; all evidence saved in {folder/'summary.json'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT/"data/measurement-public")
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data/measurement-undistortion")
    parser.add_argument("--runtime-dir", type=Path, default=ROOT/"data/measurement-public/runtime")
    parser.add_argument("--runtime-root", type=Path, default=ROOT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--freeze-selection", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--run-name", default="2026-11-01-e08-primary")
    parser.add_argument("--conditions", choices=["original", "rectified"], nargs="+",
                        default=["original", "rectified"])
    parser.add_argument("--device", choices=["auto", "mps", "cuda", "cpu"], default="auto")
    args = parser.parse_args()
    data_root, source_root = args.data_dir.resolve(), args.source_dir.resolve()
    data_root.mkdir(parents=True, exist_ok=True)
    if args.download:
        download_sources(source_root, json.loads(E07.read_text()))
    if args.prepare or args.freeze_selection:
        prepare(source_root, data_root, args.freeze_selection)
    if args.run:
        run(args, json.loads(PROTOCOL.read_text()))


if __name__ == "__main__":
    main()
