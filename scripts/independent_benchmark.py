#!/usr/bin/env python3
"""E10-M independent real scenes; use only RGB in the unchanged VGGT worker."""

import argparse
import json
import shutil
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from PIL import __version__ as pillow_version
from public_metric_benchmark import check_file, sha256, write_json
from pv3d.metric_benchmark import camera_project, photo_to_grid, read_depth, reference_point
from pv3d.reconstruction import VGGT_CODE_REVISION, VGGT_REVISION, image_layout, prepare_images
from pv3d.undistortion import (
    bilinear_footprint,
    full_field_camera,
    model_support_mask,
    pinhole_to_source,
    project_pinhole,
    rectify_rgb,
)
from resize_benchmark import CONFIG, run, verify_prepared
from undistortion_benchmark import array_sha, boundary_projection_margin, save_lossless

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/"docs/measurement/independent-sources.json"
PROTOCOL = ROOT/"docs/measurement/independent-selection.json"


def camera_for_views(calibration_dir, names):
    rows = [line.split() for line in (calibration_dir/"cameras.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")]
    cameras = {int(row[0]): {"id": int(row[0]), "model": row[1], "size": list(map(int, row[2:4])),
                            "params": list(map(float, row[4:]))} for row in rows}
    images = {}
    for line in (calibration_dir/"images.txt").read_text().splitlines():
        words = line.split()
        if len(words) == 10 and words[-1].lower().endswith(".jpg"):
            images[Path(words[-1]).name] = {"camera_id": int(words[8]), "pose": list(map(float, words[1:8]))}
    ids = [images[name]["camera_id"] for name in names]
    if len(set(ids)) != 1:
        raise ValueError("MIXED_SELECTED_CAMERAS")
    camera = cameras[ids[0]]
    if camera["model"] != "THIN_PRISM_FISHEYE" or len(camera["params"]) != 12:
        raise ValueError("UNSUPPORTED_REFERENCE_CAMERA")
    return camera, ids, [images[name]["pose"] for name in names]


def verify_independence(selection, previous):
    old_ids, old_hashes = set(), set()
    for protocol in previous:
        for scene in protocol["scenes"]:
            old_ids.add(scene["id"])
            for view in scene.get("views", scene.get("source_views", [])):
                old_hashes.add(view["sha256"])
    for scene in selection["scenes"]:
        if scene["id"] in old_ids:
            raise ValueError("SCENE_OVERLAP")
        if any(v["sha256"] in old_hashes for v in scene["views"]):
            raise ValueError("PHOTO_OVERLAP")


def fixed_mappings(scene, condition, layout, mask):
    mappings = []
    size, params = scene["camera"]["size"], scene["camera"]["params"]
    for i, point in enumerate(scene["fixed_points"]):
        xyz = np.asarray(point["physical_xyz_m"])
        original = camera_project(xyz[:2]/xyz[2], params)-.5
        np.testing.assert_allclose(original, point["source_pixel_xy"], atol=1e-6, rtol=0)
        photo = original if condition == "original" else project_pinhole(xyz, scene["rectified_camera_K_colmap"])
        recovered = photo if condition == "original" else pinhole_to_source(photo, params, scene["rectified_camera_K_colmap"])
        residual = float(np.linalg.norm(recovered-original))
        if residual > 1e-6:
            raise ValueError("FIXED_PHYSICAL_POINT_MAPPING_CHANGED")
        grid = photo_to_grid(photo, layout["mapping_rect"], size)
        neighbours, weights = bilinear_footprint(grid, layout["rect"], mask)
        mappings.append({"physical_point_index": i, "photo_xy": photo.tolist(), "grid_xy": grid,
                         "roundtrip_residual_source_px": residual,
                         "neighbours": [{"xy": list(map(int, p)), "weight": float(w)}
                                        for p, w in zip(neighbours, weights, strict=True)]})
    return mappings


def download(data_root, source):
    """Only selected members; never unpack every ~100MB reference depth map."""
    for scene in source["scenes"]:
        for archive in scene["archives"]:
            path = data_root/"archives"/archive["filename"]
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                temporary = path.with_suffix(".part")
                with urllib.request.urlopen(archive["url"], timeout=120) as response, temporary.open("wb") as output:
                    while chunk := response.read(1024*1024):
                        output.write(chunk)
                temporary.rename(path)
            check_file(path, archive["sha256"])
            members = archive["selected_members"]
            destination = data_root/"source-data"
            destination.mkdir(exist_ok=True)
            if all((destination/member).exists() for member in members):
                continue
            extractor = shutil.which("7zz") or shutil.which("7z")
            if not extractor:
                raise RuntimeError("Install 7-Zip (7zz/7z); bsdtar3.5.3 produced zero-filled ETH3D depth files")
            subprocess.run([extractor, "x", str(path), f"-o{destination}", "-y", *members], check=True)
    verify_source_files(data_root, source)


def verify_source_files(data_root, source):
    previous = [json.loads((ROOT/"docs/measurement"/name).read_text()) for name in
                ["public-metric-selection.json", "undistortion-selection.json", "resize-selection.json"]]
    verify_independence(source, previous)
    for scene in source["scenes"]:
        for file in [*scene["views"], *scene["reference_files"]]:
            check_file(data_root/"source-data"/file["path"], file["sha256"])
        camera, ids, _ = camera_for_views(data_root/"source-data"/scene["id"]/"dslr_calibration_jpg",
                                         [Path(v["path"]).name for v in scene["views"]])
        assert camera == scene["camera"] and ids == scene["selected_camera_ids"]
        depth_file = next(f for f in scene["reference_files"] if "/ground_truth_depth/" in f["path"])
        depth = read_depth(data_root/"source-data"/depth_file["path"], *camera["size"])
        for index, point in enumerate(scene["reference_points"]):
            measured = reference_point(depth, point["requested_pixel_xy"], camera["params"])
            for field, value in measured.items():
                expected, stored = np.asarray(value, dtype=float), np.asarray(point.get(field), dtype=float)
                tolerance = 1e-9 if field == "xyz_m" else 1e-12
                if (stored.shape != expected.shape or not np.isfinite(stored).all()
                    or not np.allclose(stored, expected, atol=tolerance, rtol=0)):
                    raise ValueError(f"INDEPENDENT_SCAN_REFERENCE_CHANGED: {scene['id']}/{index}/{field}")
        xyz = np.array([p["xyz_m"] for p in scene["reference_points"]])
        assert xyz.shape == (10, 3) and np.isfinite(xyz).all()
        for j, segment in enumerate(scene["segments"]):
            a, b = segment["point_indices"]
            np.testing.assert_allclose(np.linalg.norm(xyz[a]-xyz[b])*1000, scene["reference_lengths_mm"][j], atol=1e-9)


def prepare(args):
    source = json.loads(SOURCE.read_text())
    data_root = args.data_dir.resolve()
    verify_source_files(data_root, source)
    cv2.setNumThreads(4)
    protocol = {"schema_version": 1, "experiment_id": "E10-M", "created_at": datetime.now(UTC).isoformat(),
                "inference_started_at_freeze": False, "baseline_commit": "66fd7cc",
                "source_selection_sha256": sha256(SOURCE), "model_revision": VGGT_REVISION,
                "model_code_revision": VGGT_CODE_REVISION, "configuration": CONFIG,
                "versions": {"numpy": np.__version__, "opencv": cv2.__version__, "pillow": pillow_version}, "scenes": []}
    timings = []
    for selected in source["scenes"]:
        started = time.perf_counter()
        name, camera = selected["id"], selected["camera"]
        size, params = camera["size"], camera["params"]
        k = full_field_camera(params, size, samples=257, margin=.002)
        scene = {"id": name, "camera": camera, "source_views": selected["views"],
                 "selected_camera_ids": selected["selected_camera_ids"],
                 "segments": selected["segments"], "reference_lengths_mm": selected["reference_lengths_mm"],
                 "fixed_points": [{"physical_xyz_m": p["xyz_m"], "source_pixel_xy": p["sample_pixel_xy"],
                                   "source_depth_z_m": p["depth_z_m"]} for p in selected["reference_points"]],
                 "rectified_camera_K_colmap": k.tolist(),
                 "source_boundary_min_margin_px": boundary_projection_margin(params, size, k), "cases": []}
        for condition in CONFIG["image_conditions"]:
            inputs, paths, valid = [], [], None
            warp_ms = 0.
            for view in selected["views"]:
                original_path = data_root/"source-data"/view["path"]
                with Image.open(original_path) as image:
                    rgb = np.asarray(image.convert("RGB"))
                if condition == "rectified":
                    begin = time.perf_counter()
                    rgb, new_valid = rectify_rgb(rgb, params, k)
                    warp_ms += (time.perf_counter()-begin)*1000
                else:
                    new_valid = np.ones(rgb.shape[:2], bool)
                if valid is None:
                    valid = new_valid
                else:
                    np.testing.assert_array_equal(valid, new_valid)
                path = data_root/"inputs"/name/condition/(original_path.stem+".png")
                save_lossless(path, rgb)
                inputs.append({"path": str(path.relative_to(data_root)), "file_sha256": sha256(path),
                               "rgb_sha256": array_sha(rgb), "original_jpeg_sha256": view["sha256"]})
                paths.append(path)
            for mode in CONFIG["resize_modes"]:
                tensors, rects = prepare_images(paths, 518, resize_mode=mode)
                layout = image_layout(*size, 518, mode)
                assert all(r.tolist() == layout["rect"] for r in rects)
                mask = model_support_mask(valid, layout["rect"], 518, mapping_rect=layout["mapping_rect"])
                folder = data_root/"prepared"/name/f"{condition}-{mode}"
                folder.mkdir(parents=True, exist_ok=True)
                mask_path, preview = folder/"support.npy", folder/"model-input-view0.png"
                if mask_path.exists():
                    np.testing.assert_array_equal(np.load(mask_path, allow_pickle=False), mask)
                else:
                    np.save(mask_path, mask, allow_pickle=False)
                save_lossless(preview, np.rint(tensors[0].transpose(1, 2, 0)*255).astype(np.uint8))
                scene["cases"].append({"image_condition": condition, "resize_mode": mode, "inputs": inputs,
                    "layout": layout, "rect": layout["rect"], "mapping_rect": layout["mapping_rect"],
                    "input_tensor_sha256": array_sha(tensors), "point_mappings": fixed_mappings(scene, condition, layout, mask),
                    "support_mask": str(mask_path.relative_to(data_root)), "support_mask_sha256": sha256(mask_path),
                    "input_preview": str(preview.relative_to(data_root)), "input_preview_sha256": sha256(preview),
                    "model_valid_pixel_count": int(mask.sum()), "photo_invalid_fraction": float(1-valid.mean())})
            timings.append({"scene": name, "condition": condition, "warp_rgb_ms": warp_ms})
        protocol["scenes"].append(scene)
        print(f"Prepared {name}/4 policies in {time.perf_counter()-started:.1f}s", flush=True)
    if args.freeze_selection:
        if PROTOCOL.exists():
            raise ValueError("Protocol already frozen; never overwrite it")
        write_json(PROTOCOL, protocol)
    else:
        expected = json.loads(PROTOCOL.read_text())
        for key in ["source_selection_sha256", "model_revision", "model_code_revision", "configuration", "scenes"]:
            if protocol[key] != expected[key]:
                raise ValueError(f"INDEPENDENT_PROTOCOL_CHANGED: {key}")
    write_json(data_root/"preparation.json", {"protocol_sha256": sha256(PROTOCOL), "actual_versions": protocol["versions"], "timings": timings})
    print("Frozen/verified protocol", sha256(PROTOCOL), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data/measurement-independent")
    parser.add_argument("--runtime-dir", type=Path, default=ROOT/"data/measurement-public/runtime")
    parser.add_argument("--runtime-root", type=Path, default=ROOT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--freeze-selection", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--run-name", default="2026-11-01-e10m-primary")
    parser.add_argument("--reverse-order", action="store_true")
    parser.add_argument("--image-conditions", nargs="+", choices=CONFIG["image_conditions"], default=CONFIG["image_conditions"])
    parser.add_argument("--resize-modes", nargs="+", choices=CONFIG["resize_modes"], default=CONFIG["resize_modes"])
    parser.add_argument("--scenes", nargs="+")
    parser.add_argument("--device", choices=["auto", "mps", "cuda", "cpu"], default="auto")
    args = parser.parse_args()
    args.image_dir = args.data_dir
    args.protocol_path = PROTOCOL
    args.data_dir.mkdir(parents=True, exist_ok=True)
    if args.download:
        download(args.data_dir.resolve(), json.loads(SOURCE.read_text()))
    if args.prepare or args.freeze_selection:
        prepare(args)
    if args.verify or args.run:
        verify_source_files(args.data_dir.resolve(), json.loads(SOURCE.read_text()))
        protocol = json.loads(PROTOCOL.read_text())
        assert protocol["source_selection_sha256"] == sha256(SOURCE)
        verify_prepared(args, protocol)
        if args.run:
            if args.scenes:
                if not set(args.scenes) <= {s["id"] for s in protocol["scenes"]}:
                    raise ValueError("UNKNOWN_SCENE")
                protocol["scenes"] = [s for s in protocol["scenes"] if s["id"] in args.scenes]
            run(args, protocol)


if __name__ == "__main__":
    main()
