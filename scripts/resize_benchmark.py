#!/usr/bin/env python3
"""E09: fixed physical points, legacy14 versus isotropic518 preprocessing."""

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
from httpx import HTTPError
from PIL import Image
from PIL import __version__ as pillow_version
from public_metric_benchmark import check_file, download_sources, evaluate_api, seed_job, sha256, write_json
from pv3d.metric_benchmark import grid_to_photo, photo_to_grid
from pv3d.reconstruction import VGGT_REVISION, VggtReconstructor, image_layout, load_geometry, prepare_images
from pv3d.store import Store
from pv3d.undistortion import bilinear_footprint, model_support_mask, sample_camera_depth
from undistortion_benchmark import E07, array_sha, point_diagnostics
from undistortion_benchmark import PROTOCOL as E08_PROTOCOL
from undistortion_benchmark import prepare as prepare_e08
from undistortion_benchmark import verify_prepared as verify_e08

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/"docs/measurement/resize-selection.json"
ARCHIVE = ROOT/"docs/measurement/undistortion-results.json"
CONFIG = {"input_size": 518, "resize_modes": ["legacy14", "isotropic"],
          "image_conditions": ["original", "rectified"], "filter": "PIL BICUBIC, reducing_gap=None",
          "isotropic": "one scalar; centered fractional content; floor/ceil storage; inverse-affine floating source box",
          "border": "white short-axis source padding covers bicubic footprint; unchanged legacy14 borders",
          "support": "source erosion ceil(2*max_inverse_scale)+2; inverse mapping; all four neighbours valid",
          "sampling": "E08 bilinear camera-Z then predicted-K/extrinsic; same physical points, no snapping",
          "primary_stratum": "rectified", "auxiliary_K": "rectified only, separate A-B-only scale"}


def prepare(args):
    source = json.loads(E08_PROTOCOL.read_text())
    image_root, data_root = args.image_dir.resolve(), args.data_dir.resolve()
    if not (image_root/"inputs").exists():
        prepare_e08(args.source_dir.resolve(), image_root, False)
    verify_e08(image_root, source)
    protocol = {"schema_version": 1, "experiment_id": "E09", "created_at": datetime.now(UTC).isoformat(),
                "inference_started_at_freeze": False, "baseline_commit": "cf98129",
                "e08_protocol_sha256": sha256(E08_PROTOCOL), "e08_results_sha256": sha256(ARCHIVE),
                "model_revision": source["model_revision"], "model_code_revision": source["model_code_revision"],
                "configuration": CONFIG, "versions": {"numpy": np.__version__, "pillow": pillow_version}, "scenes": []}
    for old in source["scenes"]:
        scene = {k: v for k, v in old.items() if k != "conditions"}
        scene["cases"] = []
        width, height = scene["camera"]["size"]
        for condition in CONFIG["image_conditions"]:
            fixed = old["conditions"][condition]
            paths = [image_root/p["path"] for p in fixed["inputs"]]
            valid = np.asarray(Image.open(image_root/Path(fixed["support_mask"]).with_name("photo-valid.png"))) > 0
            for mode in CONFIG["resize_modes"]:
                started = time.perf_counter()
                tensors, rects = prepare_images(paths, 518, resize_mode=mode)
                layout = image_layout(width, height, 518, mode)
                assert all(r.tolist() == layout["rect"] for r in rects)
                mask = model_support_mask(valid, layout["rect"], 518, mapping_rect=layout["mapping_rect"])
                folder = data_root/"prepared"/scene["id"]/f"{condition}-{mode}"
                folder.mkdir(parents=True, exist_ok=True)
                mask_path = folder/"support.npy"
                if mask_path.exists():
                    np.testing.assert_array_equal(np.load(mask_path, allow_pickle=False), mask)
                else:
                    np.save(mask_path, mask, allow_pickle=False)
                preview = folder/"model-input-view0.png"
                rgb = np.rint(tensors[0].transpose(1, 2, 0)*255).astype(np.uint8)
                if preview.exists():
                    np.testing.assert_array_equal(np.asarray(Image.open(preview)), rgb)
                else:
                    Image.fromarray(rgb).save(preview)
                mappings = []
                for p in fixed["point_mappings"]:
                    grid = photo_to_grid(p["photo_xy"], layout["mapping_rect"], [width, height])
                    recovered = grid_to_photo(grid, layout["mapping_rect"], [width, height])
                    residual = float(np.linalg.norm(np.asarray(recovered)-p["photo_xy"]))
                    assert residual < 1e-6
                    neighbours, weights = bilinear_footprint(grid, layout["rect"], mask)
                    mappings.append({"physical_point_index": p["physical_point_index"], "photo_xy": p["photo_xy"],
                                     "grid_xy": grid, "roundtrip_residual_photo_px": residual,
                                     "neighbours": [{"xy": list(map(int, xy)), "weight": float(w)}
                                                    for xy, w in zip(neighbours, weights, strict=True)]})
                selected = {"image_condition": condition, "resize_mode": mode, "inputs": fixed["inputs"],
                            "layout": layout, "rect": layout["rect"], "mapping_rect": layout["mapping_rect"],
                            "input_tensor_sha256": array_sha(tensors), "point_mappings": mappings,
                            "support_mask": str(mask_path.relative_to(data_root)), "support_mask_sha256": sha256(mask_path),
                            "input_preview": str(preview.relative_to(data_root)), "input_preview_sha256": sha256(preview),
                            "model_valid_pixel_count": int(mask.sum())}
                if mode == "legacy14":
                    assert selected["input_tensor_sha256"] == fixed["input_tensor_sha256"]
                    check_file(mask_path, fixed["support_mask_sha256"])
                    for a, b in zip(mappings, fixed["point_mappings"], strict=True):
                        np.testing.assert_allclose(a["grid_xy"], b["grid_xy"], atol=1e-12, rtol=0)
                scene["cases"].append(selected)
                print(f"Prepared {scene['id']}/{condition}/{mode}: {time.perf_counter()-started:.2f}s", flush=True)
        protocol["scenes"].append(scene)
    if args.freeze_selection:
        if PROTOCOL.exists():
            raise ValueError("Resize protocol already frozen; never overwrite it")
        write_json(PROTOCOL, protocol)
    else:
        expected = json.loads(PROTOCOL.read_text())
        for key in ["e08_protocol_sha256", "e08_results_sha256", "model_revision", "model_code_revision", "configuration", "scenes"]:
            if protocol[key] != expected[key]:
                raise ValueError(f"RESIZE_PROTOCOL_CHANGED: {key}")
    print(f"Resize protocol verified/frozen: {sha256(PROTOCOL)}", flush=True)


def verify_prepared(args, protocol):
    assert protocol["e08_protocol_sha256"] == sha256(E08_PROTOCOL)
    assert protocol["e08_results_sha256"] == sha256(ARCHIVE)
    assert protocol["configuration"] == CONFIG
    for scene in protocol["scenes"]:
        for case in scene["cases"]:
            paths = [args.image_dir.resolve()/p["path"] for p in case["inputs"]]
            for path, p in zip(paths, case["inputs"], strict=True):
                check_file(path, p["file_sha256"])
            for path, key in [(case["support_mask"], "support_mask_sha256"), (case["input_preview"], "input_preview_sha256")]:
                check_file(args.data_dir.resolve()/path, case[key])
            tensor, rects = prepare_images(paths, 518, resize_mode=case["resize_mode"])
            if array_sha(tensor) != case["input_tensor_sha256"]:
                raise ValueError("RESIZE_MODEL_TENSOR_CHANGED")
            assert all(r.tolist() == case["rect"] for r in rects)


def preview_asset(runtime, preview):
    """JPEG viewer derivative only; immutable lossless tensor preview stays local."""
    store, identifier = Store(runtime), uuid4().hex
    folder = runtime/"assets"/identifier
    folder.mkdir()
    with Image.open(preview) as image:
        image.convert("RGB").save(folder/"image.jpg", quality=95, subsampling=0)
    store.add_asset({"id": identifier, "width": 518, "height": 518, "sha256": sha256(folder/"image.jpg")})
    return store.get_asset(identifier)["image_url"]


def run(args, protocol):
    verify_prepared(args, protocol)
    data_root, runtime, runtime_root = args.data_dir.resolve(), args.runtime_dir.resolve(), args.runtime_root.resolve()
    folder = data_root/"runs"/args.run_name
    if (folder/"summary.json").exists():
        raise ValueError("Frozen run exists; choose another --run-name")
    folder.mkdir(parents=True, exist_ok=True)
    weights = runtime_root/"models/huggingface/models--facebook--VGGT-1B/snapshots"/VGGT_REVISION/"model.safetensors"
    check_file(weights, "f164acf60724910d8fe1578bb499d800850c7bb0948db7555c413f9fbe60467e")
    files = [Path(__file__), ROOT/"services/api/src/pv3d/reconstruction.py", ROOT/"services/api/src/pv3d/undistortion.py",
             ROOT/"services/multiview/infer.py"]
    summary = {"schema_version": 1, "experiment_id": "E09", "created_at": datetime.now(UTC).isoformat(),
               "protocol_sha256": sha256(PROTOCOL), "configuration": CONFIG, "order_reversed": args.reverse_order,
               "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "code_file_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in files}, "runs": []}
    cases = [(scene, case) for scene in protocol["scenes"] for case in scene["cases"]
             if case["image_condition"] in args.image_conditions and case["resize_mode"] in args.resize_modes]
    if args.reverse_order:
        cases.reverse()
    archive = json.loads(ARCHIVE.read_text())
    for scene, case in cases:
        name, condition, mode = scene["id"], case["image_condition"], case["resize_mode"]
        paths = [args.image_dir.resolve()/p["path"] for p in case["inputs"]]
        destination = folder/f"{name}-{condition}-{mode}"
        row = {"scene": name, "image_condition": condition, "resize_mode": mode, "input_size": 518, "view_count": 3,
               "reference_lengths_mm": scene["reference_lengths_mm"], "layout": case["layout"], "status": "running"}
        summary["runs"].append(row)
        write_json(folder/"summary.json", summary)
        started = time.perf_counter()
        try:
            worker = VggtReconstructor(runtime_python=runtime_root/"services/multiview/.venv/bin/python",
                worker_script=ROOT/"services/multiview/infer.py", cache_dir=runtime_root/"models/huggingface",
                device=args.device, input_size=518, resize_mode=mode)
            meta = worker.reconstruct(paths, destination,
                lambda stage, label=f"{name}/{condition}/{mode}": print(f"{label}: {stage}", flush=True))
            row["worker_wall_ms"] = (time.perf_counter()-started)*1000
            assert meta["input_tensor_sha256"] == case["input_tensor_sha256"]
            assert meta["model"]["revision"] == protocol["model_revision"]
            assert meta["model"]["code_revision"] == protocol["model_code_revision"]
            assert meta["model"]["resize_mode"] == mode
            geometry = load_geometry(destination/"geometry.npz", 3)
            assert all(r.tolist() == case["rect"] for r in geometry["rects"])
            np.testing.assert_array_equal(geometry["colors"][0], np.asarray(Image.open(data_root/case["input_preview"])))
            mask = np.load(data_root/case["support_mask"], allow_pickle=False)
            samples = [sample_camera_depth(geometry, p["grid_xy"], mask) for p in case["point_mappings"]]
            for a, b in zip(samples, case["point_mappings"], strict=True):
                assert [(p["x"], p["y"]) for p in a["neighbours"]] == [tuple(p["xy"]) for p in b["neighbours"]]
                np.testing.assert_allclose([p["weight"] for p in a["neighbours"]],
                                           [p["weight"] for p in b["neighbours"]], atol=1e-12, rtol=0)
            write_json(destination/"derived-anchor-audit.json", samples)
            points = [s["world_xyz"] for s in samples]
            eval_scene = {**scene, "resolutions": {"518": {"points": case["point_mappings"],
                                                       "reference_lengths_mm": scene["reference_lengths_mm"]}}}
            meta["model"].update(experiment_id="E09", image_condition=condition, protocol_sha256=sha256(PROTOCOL),
                                 measurement_sampling=CONFIG["sampling"])
            job, indices, job_folder = seed_job(runtime, eval_scene, paths, geometry, meta, 518,
                                                measurement_points=points, support_masks=np.tile(mask, (3, 1, 1)))
            measured, receipt = evaluate_api(runtime, job, indices, eval_scene, 518, geometry,
                point_component_id="measurement-anchors", expected_positions=points,
                source_note=f"E09 ETH3D {name}/{condition}/{mode}; fixed scanner points; derived camera-Z anchors; GT withheld.")
            write_json(destination/"receipt.json", receipt)
            diagnostic_scene = {**scene, "conditions": {condition: {"rect": case["mapping_rect"]}}}
            diagnostics = point_diagnostics(diagnostic_scene, condition, samples, geometry, measured["calibration"]["mm_per_unit"])
            write_json(destination/"diagnostics.json", diagnostics)
            row.update(status="succeeded", model=meta["model"], input_tensor_sha256=meta["input_tensor_sha256"],
                       model_timings=meta["timings"], **measured, diagnostics=diagnostics,
                       raw_cloud_sha256=sha256(job_folder/"raw-cloud.glb"),
                       input_preview_url=preview_asset(runtime, data_root/case["input_preview"]),
                       preview_points=[{"id": chr(65+i), "uv": [(p["grid_xy"][0]+.5)/518, (p["grid_xy"][1]+.5)/518]}
                                       for i, p in enumerate(case["point_mappings"])])
            if mode == "legacy14":
                previous = next(r for r in archive["runs"] if (r["scene"], r["condition"]) == (name, condition))
                row["e08_audit_cloud_matches"] = row["geometry_sha256"] == previous["geometry_sha256"]
                assert row["e08_audit_cloud_matches"]
                assert row["raw_cloud_sha256"] == previous["raw_cloud_sha256"]
                old_path = args.image_dir.resolve()/f"runs/2026-11-01-e08-primary/{name}-{condition}/geometry.npz"
                if old_path.exists():
                    old = load_geometry(old_path, 3)
                    row["model_arrays_equal_e08"] = all(np.array_equal(v, old[k]) for k, v in geometry.items())
                    assert row["model_arrays_equal_e08"]
                np.testing.assert_array_equal([c["calibrated_mm"] for c in row["checks"]],
                                              [c["calibrated_mm"] for c in previous["checks"]])
            print(f"{name}/{condition}/{mode} errors%: {[round(c['relative_error_pct'], 3) for c in row['checks']]}", flush=True)
        except (OSError, ValueError, RuntimeError, AssertionError, HTTPError) as error:
            row.update(status="failed", error=f"{type(error).__name__}: {error}",
                       failed_wall_ms=(time.perf_counter()-started)*1000)
            print(row["error"], flush=True)
        write_json(folder/"summary.json", summary)
    print(f"Summary: {folder/'summary.json'}", flush=True)
    if not cases or any(r["status"] != "succeeded" for r in summary["runs"]):
        raise SystemExit("E09 incomplete or failed; evidence preserved in summary.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT/"data/measurement-public")
    parser.add_argument("--image-dir", type=Path, default=ROOT/"data/measurement-undistortion")
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data/measurement-resize")
    parser.add_argument("--runtime-dir", type=Path, default=ROOT/"data/measurement-public/runtime")
    parser.add_argument("--runtime-root", type=Path, default=ROOT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--freeze-selection", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--run-name", default="2026-11-01-e09-primary")
    parser.add_argument("--reverse-order", action="store_true")
    parser.add_argument("--image-conditions", choices=CONFIG["image_conditions"], nargs="+", default=CONFIG["image_conditions"])
    parser.add_argument("--resize-modes", choices=CONFIG["resize_modes"], nargs="+", default=CONFIG["resize_modes"])
    parser.add_argument("--device", choices=["auto", "mps", "cuda", "cpu"], default="auto")
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    if args.download:
        download_sources(args.source_dir.resolve(), json.loads(E07.read_text()))
    if args.prepare or args.freeze_selection:
        prepare(args)
    if args.run:
        run(args, json.loads(PROTOCOL.read_text()))


if __name__ == "__main__":
    main()
