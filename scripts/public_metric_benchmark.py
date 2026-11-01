#!/usr/bin/env python3
"""Reproduce E07 from public ETH3D images, without feeding reference data to VGGT."""

import argparse
import hashlib
import json
import shutil
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import HTTPError
from PIL import Image, ImageDraw
from pv3d.measurement import register_measurement_routes
from pv3d.metric_benchmark import read_depth, reference_point
from pv3d.multiview_schemas import MultiResult
from pv3d.pointcloud import export_pointcloud
from pv3d.reconstruction import VggtReconstructor, load_geometry
from pv3d.store import Store

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "docs/measurement/public-metric-selection.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n")


def check_file(path, expected):
    if not path.is_file() or sha256(path) != expected:
        raise ValueError(f"Missing or changed source: {path}")


def download_sources(root, selection):
    """Use system libarchive tar on macOS, or 7zz/7z on Linux. No account needed."""
    for scene in selection["scenes"]:
        for archive in scene["archives"]:
            path = root / "sources" / archive["name"]
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                print(f"Downloading {archive['url']}", flush=True)
                part = path.with_suffix(path.suffix+".part")
                with urllib.request.urlopen(archive["url"], timeout=60) as response, part.open("wb") as target:
                    shutil.copyfileobj(response, target)
                check_file(part, archive["sha256"])
                part.rename(path)
            check_file(path, archive["sha256"])
            output = root / "source-data"
            output.mkdir(parents=True, exist_ok=True)
            seven = shutil.which("7zz") or shutil.which("7z")
            command = ([seven, "x", "-y", f"-o{output}", str(path)] if seven else
                       ["tar", "-xf", str(path), "-C", str(output)])
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL)


def verify_sources(root, selection):
    for scene in selection["scenes"]:
        for item in [*scene["views"], scene["camera"], scene["depth"]]:
            check_file(root / "source-data" / item["path"], item["sha256"])
        depth = read_depth(root / "source-data" / scene["depth"]["path"], *scene["camera"]["size"])
        for resolution in scene["resolutions"].values():
            for point in resolution["points"]:
                recomputed = reference_point(depth, point["photo_xy"], scene["camera"]["params"])
                np.testing.assert_allclose(recomputed["xyz_m"], point["xyz_m"], atol=1e-10, rtol=0)
    print("Source hashes and frozen metric reference points verified", flush=True)


def seed_job(runtime, scene, paths, geometry, metadata, input_size, *,
             measurement_points=None, support_masks=None):
    store = Store(runtime)
    assets = []
    for path in paths:
        identifier = uuid4().hex
        folder = runtime / "assets" / identifier
        folder.mkdir()
        with Image.open(path) as image:
            width, height = image.size
            if image.format == "JPEG":
                shutil.copyfile(path, folder / "image.jpg")
            else:
                # Viewer preview only. Model inference reads the lossless source path.
                image.convert("RGB").save(folder / "image.jpg", quality=95, subsampling=0)
        store.add_asset({"id": identifier, "width": width, "height": height,
                         "sha256": sha256(folder / "image.jpg")})
        assets.append(store.get_asset(identifier))
    capture = store.create_capture([a["id"] for a in assets])
    job = store.create_multiview_job(capture["id"], len(assets))
    folder = runtime / "multiview" / job["id"]
    vertices, colors, groups, components, observations = [], [], [], [], []
    endpoint_indices = []
    reference = scene["resolutions"][str(input_size)]
    for i, asset in enumerate(assets):
        left, top, right, bottom = geometry["rects"][i]
        valid = np.zeros(geometry["depth"][i].shape, bool)
        valid[top:bottom, left:right] = True
        valid &= np.isfinite(geometry["points"][i]).all(axis=-1) & (geometry["depth"][i] > 0)
        if support_masks is not None:
            valid &= support_masks[i]
        flat = np.flatnonzero(valid)
        if i == 0 and measurement_points is None:
            lookup = {int(value): j for j, value in enumerate(flat)}
            for point in reference["points"]:
                x, y = point["grid_xy"]
                if int(y*input_size+x) not in lookup:
                    raise ValueError("Selected endpoint has no finite predicted point; retain run as failed")
                endpoint_indices.append(lookup[int(y*input_size+x)])
        points = geometry["points"][i][valid] * [1, -1, -1]
        identifier = f"benchmark-view-{i}"
        observation_id = f"benchmark-observation-{i}"
        components.append({"id": identifier, "category": "unknown", "label": f"{scene['id']} / view {i+1}",
                           "source": "manual", "score": None, "observation_ids": [observation_id],
                           "point_count": len(points), "color": "#88b8ac",
                           "position": np.mean(points, axis=0).tolist(), "dimensions": np.ptp(points, axis=0).tolist()})
        observations.append({"id": observation_id, "component_id": identifier, "asset_id": asset["id"],
                             "category": "unknown", "label": components[-1]["label"],
                             "bbox": [0, 0, 1, 1], "source": "manual", "score": None})
        vertices.append(points); colors.append(geometry["colors"][i][valid]); groups.append(np.full(len(points), i+1))
    def export():
        return export_pointcloud({"vertices": np.concatenate(vertices).astype(np.float32),
                                  "colors": np.concatenate(colors), "indices": np.concatenate(groups),
                                  "components": components}, folder)
    export()
    if measurement_points is not None:
        for name in ["cloud.glb", "cloud.ply", "component-map.json"]:
            shutil.copyfile(folder/name, folder/("raw-"+name))
        anchors = np.asarray(measurement_points, dtype=np.float64) * [1, -1, -1]
        if anchors.ndim != 2 or anchors.shape[1] != 3 or not np.isfinite(anchors).all():
            raise ValueError("Invalid derived measurement anchors")
        identifier, observation_id = "measurement-anchors", "derived-anchor-observation"
        components.append({"id": identifier, "category": "unknown", "label": "Derived fixed-position samples",
                           "source": "manual", "score": None, "observation_ids": [observation_id],
                           "point_count": len(anchors), "color": "#ffb547",
                           "position": np.mean(anchors, axis=0).tolist(),
                           "dimensions": np.ptp(anchors, axis=0).tolist()})
        observations.append({"id": observation_id, "component_id": identifier, "asset_id": assets[0]["id"],
                             "category": "unknown", "label": components[-1]["label"], "bbox": [0, 0, 1, 1],
                             "source": "manual", "score": None})
        vertices.append(anchors); colors.append(np.tile([255, 181, 71], (len(anchors), 1)).astype(np.uint8))
        groups.append(np.full(len(anchors), len(components)))
        endpoint_indices = list(range(len(anchors)))
        export()
    prefix = f"/api/multiview/jobs/{job['id']}"
    result = MultiResult.model_validate({"job_id": job["id"], "capture_id": capture["id"],
        "geometry_job_id": job["id"], "views": assets, "observations": observations,
        "components": components, "scene_url": prefix+"/cloud.glb", "ply_url": prefix+"/cloud.ply",
        "json_url": prefix+"/result.json", "point_count": sum(len(v) for v in vertices), "context_point_count": 0,
        "model": {**metadata["model"], "read_only_geometry": True},
        "quality": {"evidence_scope": "public metric geometry audit; groups are views/derived samples, not parts",
                    "derived_anchor_count": 0 if measurement_points is None else len(measurement_points)},
        "timings": metadata["timings"], "warnings": ["PUBLIC_SCAN_REFERENCE_NOT_FIELD_CERTIFICATION",
            "WHOLE_SCENE_AUDIT_NOT_PV_COMPONENT_RECOGNITION"] +
            (["DERIVED_SUBPIXEL_ANCHORS_NOT_RAW_POINTS"] if measurement_points is not None else [])
        }).model_dump(mode="json")
    write_json(folder / "result.json", result)
    store.update_multiview_job(job["id"], status="needs_review", stage="complete", result=result)
    return job["id"], endpoint_indices, folder


def evaluate_api(runtime, job_id, indices, scene, input_size, geometry, *,
                 point_component_id="benchmark-view-0", expected_positions=None, source_note=None):
    base = f"/api/multiview/jobs/{job_id}/measurements"
    reference = scene["resolutions"][str(input_size)]
    timings = []
    # Use the real measurement handlers without starting a job runner/lifespan:
    # create_app.interrupt_unfinished() would alter unrelated shared-runtime jobs.
    app = FastAPI()
    app.state.store = Store(runtime)
    register_measurement_routes(app)
    with TestClient(app) as client:
        fingerprint = client.get(base).json()["geometry_sha256"]
        def post(path, data):
            started = time.perf_counter()
            response = client.post(path, json=data)
            response.raise_for_status()
            timings.append((time.perf_counter()-started)*1000)
            return response.json()
        def pair(segment):
            return [{"component_id": point_component_id, "point_index": indices[i]}
                    for i in segment["point_indices"]]
        def audit(record, segment):
            for resolved, point_id in zip(record["points"], segment["point_indices"], strict=True):
                if expected_positions is None:
                    x, y = reference["points"][point_id]["grid_xy"]
                    expected = geometry["points"][0, y, x]
                else:
                    expected = np.asarray(expected_positions[point_id])
                np.testing.assert_allclose(resolved["position"], expected*[1, -1, -1], atol=1e-6, rtol=1e-6)
        source = source_note or f"ETH3D {scene['id']}; scan-derived depth; GT data excluded from VGGT inputs."
        cal = post(base+"/calibrations", {"geometry_sha256": fingerprint, "points": pair(scene["segments"][0]),
            "known_length": reference["reference_lengths_mm"][0], "unit": "mm", "source_note": source,
            "label": scene["segments"][0]["label"]})
        audit(cal, scene["segments"][0])
        rows = []
        for j, segment in enumerate(scene["segments"][1:], 1):
            body = {"geometry_sha256": fingerprint, "points": pair(segment), "label": segment["label"]}
            raw = post(base, body)
            assert raw["distance_mm"] is None and raw["scale_status"] == "relative_estimate"
            measured = post(base, {**body, "calibration_id": cal["id"], "validation": {
                "known_length": reference["reference_lengths_mm"][j], "unit": "mm", "source_note": source}})
            # Audit the actual original GLB positions read by the API, not client-made coordinates.
            audit(measured, segment)
            np.testing.assert_allclose(measured["distance_mm"], raw["distance_units"]*cal["mm_per_unit"], rtol=1e-9)
            assert measured["validation"]["used_for_calibration"] is False
            rows.append({"segment_id": segment["id"], "label": segment["label"],
                         "reference_mm": reference["reference_lengths_mm"][j],
                         "relative_distance_u": raw["distance_units"], "calibrated_mm": measured["distance_mm"],
                         "absolute_error_mm": measured["validation"]["absolute_error_mm"],
                         "relative_error_pct": measured["validation"]["relative_error_pct"],
                         "measurement_record_id": measured["id"]})
        receipt = client.get(base+"/export.json").json()
        assert len(receipt["calibrations"]) == 1 and len(receipt["measurements"]) == 8
        assert receipt["raw_geometry_scale_status"] == "unknown"
    return {"job_id": job_id, "geometry_sha256": fingerprint, "calibration": cal,
            "checks": rows, "api_roundtrip_ms": timings}, receipt


def annotated_photo(path, scene, input_size, output):
    with Image.open(path) as source:
        image = source.convert("RGB"); image.thumbnail((1200, 800))
    draw = ImageDraw.Draw(image)
    for j, segment in enumerate(scene["segments"]):
        pts = [scene["resolutions"][str(input_size)]["points"][i] for i in segment["point_indices"]]
        positions = [(p["photo_xy"][0]/scene["camera"]["size"][0]*image.width,
                      p["photo_xy"][1]/scene["camera"]["size"][1]*image.height) for p in pts]
        color = "#ffb651" if j == 0 else "#56ffe0"
        draw.line(positions, fill=color, width=3)
        for k, (x, y) in enumerate(positions):
            draw.ellipse((x-6, y-6, x+6, y+6), fill=color, outline="black", width=2)
            draw.text((x+8, y-22), chr(65+j*2+k), fill=color, stroke_fill="black", stroke_width=2, font_size=24)
    draw.text((15, 12), f"ETH3D {scene['id']} | A-B: calibration | C-J: held-out | scan-derived reference",
              fill="white", stroke_fill="black", stroke_width=2, font_size=18)
    image.save(output, quality=90)


def run(root, selection, runtime_root, sizes, run_name, device):
    run_folder = root / "runs" / run_name
    summary_path = run_folder / "summary.json"
    if summary_path.exists():
        raise ValueError("Frozen run exists; choose a new --run-name. Never overwrite prior results.")
    run_folder.mkdir(parents=True, exist_ok=True)
    summary = {"schema_version": 1, "experiment_id": "E07", "created_at": datetime.now(UTC).isoformat(),
        "selection_sha256": sha256(SELECTION), "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dataset": selection["dataset"], "reference_kind": selection["reference_kind"],
        "license": selection["license"], "source_url": selection["source_url"], "runs": []}
    runtime = root / "runtime"
    for input_size in sizes:
        for scene in selection["scenes"]:
            destination = run_folder / f"{scene['id']}-{input_size}"
            paths = [root / "source-data" / item["path"] for item in scene["views"]]
            started = time.perf_counter()
            row = {"scene": scene["id"], "input_size": input_size, "view_count": len(paths)}
            try:
                worker = VggtReconstructor(runtime_python=runtime_root/"services/multiview/.venv/bin/python",
                    worker_script=ROOT/"services/multiview/infer.py", cache_dir=runtime_root/"models/huggingface",
                    device=device, input_size=input_size)
                metadata = worker.reconstruct(paths, destination,
                    lambda stage, label=f"{scene['id']} {input_size}": print(f"{label}: {stage}", flush=True))
                row["worker_wall_ms"] = (time.perf_counter()-started)*1000
                geometry = load_geometry(destination/"geometry.npz", len(paths))
                export_start = time.perf_counter()
                job_id, indices, folder = seed_job(runtime, scene, paths, geometry, metadata, input_size)
                row["registration_export_ms"] = (time.perf_counter()-export_start)*1000
                measurement, receipt = evaluate_api(runtime, job_id, indices, scene, input_size, geometry)
                write_json(destination/"receipt.json", receipt)
                annotated_photo(paths[0], scene, input_size, destination/"reference-points.jpg")
                row.update(status="succeeded", model=metadata["model"], model_timings=metadata["timings"],
                           **measurement, glb_bytes=(folder/"cloud.glb").stat().st_size)
                print(f"{scene['id']} {input_size}: errors % " + str([
                    round(check["relative_error_pct"], 2) for check in row["checks"]]), flush=True)
            except (OSError, ValueError, RuntimeError, AssertionError, HTTPError) as error:
                row.update(status="failed", error=f"{type(error).__name__}: {error}",
                           failed_wall_ms=(time.perf_counter()-started)*1000)
                print(row["error"], flush=True)
            summary["runs"].append(row)
            write_json(summary_path, summary)
    print(f"Summary: {summary_path}", flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data/measurement-public")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--runtime-root", type=Path, default=ROOT)
    parser.add_argument("--sizes", type=int, nargs="+", choices=[336, 518], default=[336, 518])
    parser.add_argument("--run-name", default="2026-11-01-vggt-metric")
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    args = parser.parse_args()
    selection = json.loads(SELECTION.read_text())
    root = args.data_dir.resolve()
    if args.download:
        download_sources(root, selection)
    verify_sources(root, selection)
    if args.run:
        run(root, selection, args.runtime_root.resolve(), args.sizes, args.run_name, args.device)


if __name__ == "__main__":
    main()
