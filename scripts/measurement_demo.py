#!/usr/bin/env python3
"""Authored analytic point cloud and real API exercise; does not run or benchmark ML."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pv3d.app import create_app
from pv3d.multiview_schemas import MultiResult
from pv3d.pointcloud import export_pointcloud
from pv3d.store import Store


class NoModel:
    def status(self):
        return {"state": "not_loaded", "model_id": "authored-analytic-demo-no-inference", "device": "cpu"}


def draw_view(path, side):
    image = Image.new("RGB", (960, 720), "#f0f4ee")
    draw = ImageDraw.Draw(image)
    draw.text((40, 30), "AUTHORED ANALYTIC SCENE - NOT A PHOTOGRAPH", fill="#34534b", font_size=24)
    offset = 1 if side == 0 else -1
    x = 340 if side == 0 else 470
    front = [(x, 220), (x+200, 220), (x+200, 550), (x, 550)]
    back = [(a+offset*100, b-70) for a, b in front]
    draw.polygon([front[0], front[1], back[1], back[0]], fill="#bad2c4", outline="#4e7165", width=3)
    draw.polygon([front[1 if side == 0 else 0], front[2 if side == 0 else 3], back[2 if side == 0 else 3], back[1 if side == 0 else 0]], fill="#87aba3", outline="#4e7165", width=3)
    draw.polygon(front, fill="#d9e8dd", outline="#4e7165", width=3)
    for y in range(290, 420, 14): draw.line((x+40, y, x+160, y), fill="#7b9c8d", width=4)
    draw.rounded_rectangle((x+55, 455, x+145, 490), radius=5, fill="#376e65")
    draw.line((x-65, 220, x-65, 550), fill="#b88321", width=3)
    draw.text((50, 600), "Known reference: width A-B = 200 mm", fill="#34534b", font_size=24)
    draw.text((50, 640), "Held-out: height = 300 mm; distorted model height = 330 mm", fill="#34534b", font_size=21)
    image.save(path, format="JPEG", quality=90)


def build_demo(data_dir):
    manifest = data_dir / "analytic-demo.json"
    if manifest.exists():
        return json.loads(manifest.read_text())
    store = Store(data_dir)
    assets = []
    for index in range(2):
        identifier = uuid4().hex
        folder = data_dir / "assets" / identifier
        folder.mkdir()
        draw_view(folder / "image.jpg", index)
        asset = {"id": identifier, "width": 960, "height": 720,
                 "sha256": hashlib.sha256((folder / "image.jpg").read_bytes()).hexdigest()}
        store.add_asset(asset)
        assets.append(store.get_asset(identifier))
    capture = store.create_capture([a["id"] for a in assets])
    job = store.create_multiview_job(capture["id"], 2)
    folder = data_dir / "multiview" / job["id"]
    # Four widely separated endpoint markers, followed by a dense colored box shell.
    vertices = [[-1, 0, .6], [1, 0, .6], [-1, 3.3, .6], [1, 3.3, .6]]
    colors = [[255, 181, 71], [24, 197, 172], [255, 181, 71], [24, 197, 172]]
    for x in np.linspace(-1, 1, 101):
        for y in np.linspace(0, 3.3, 166):
            for z in [-.6, .6]:
                vertices.append([x, y, z])
                c = [146, 175, 159] if z < 0 else [185, 205, 187]
                if .6 < y < 2.5 and -.65 < x < .65 and int(y*50) % 7 < 2: c = [77, 111, 99]
                colors.append(c)
    for z in np.linspace(-.6, .6, 60):
        for y in np.linspace(0, 3.3, 166):
            for x in [-1, 1]:
                vertices.append([x, y, z]); colors.append([126, 164, 155])
    points = np.asarray(vertices, np.float32)
    component = {"id": "analytic-housing", "category": "cabinet", "label": "Authored analytic housing",
                 "source": "manual", "score": None, "observation_ids": ["analytic-front", "analytic-side"],
                 "point_count": len(points), "color": "#b9cdbb", "position": [0, 1.65, 0], "dimensions": [2, 3.3, 1.2]}
    export_pointcloud({"vertices": points, "colors": np.asarray(colors, np.uint8), "indices": np.ones(len(points), int),
                       "components": [component]}, folder)
    prefix = f"/api/multiview/jobs/{job['id']}"
    result = MultiResult.model_validate({"job_id": job["id"], "capture_id": capture["id"], "geometry_job_id": job["id"],
        "views": assets, "observations": [{"id": obs, "asset_id": a["id"], "component_id": component["id"],
          "category": "cabinet", "label": component["label"], "source": "manual", "score": None, "bbox": [.25, .2, .8, .85]}
          for obs, a in zip(component["observation_ids"], assets)],
        "components": [component], "scene_url": prefix + "/cloud.glb", "ply_url": prefix + "/cloud.ply",
        "json_url": prefix + "/result.json", "point_count": len(points), "context_point_count": 0,
        "model": {"model_id": "authored-analytic-fixture", "mode": "manual", "not_model_inference": True},
        "quality": {"evidence_scope": "analytic geometry, not field validation"}, "timings": {},
        "warnings": ["AUTHORED_ANALYTIC_DEMO_NOT_FIELD_ACCURACY"]}).model_dump(mode="json")
    (folder / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    store.update_multiview_job(job["id"], status="needs_review", stage="complete", result=result)
    manifest_data = {"job_id": job["id"], "data_dir": str(data_dir.resolve()),
                     "component_id": component["id"], "reference_indices": [0, 1], "height_check_indices": [0, 2],
                     "width_mm": 200, "height_mm": 300, "depth_mm": 120, "evidence_scope": "authored analytic fixture; no ML/field measurements"}
    manifest.write_text(json.dumps(manifest_data, indent=2))
    return manifest_data


def evaluate(data_dir, manifest):
    job_id = manifest["job_id"]
    base = f"/api/multiview/jobs/{job_id}/measurements"
    with TestClient(create_app(data_dir, NoModel(), reconstructor=NoModel())) as client:
        sha = client.get(base).json()["geometry_sha256"]
        ref = lambda i: {"component_id": manifest["component_id"], "point_index": i}
        def post(path, body):
            response = client.post(path, json=body)
            response.raise_for_status()
            return response.json()
        start = time.perf_counter()
        cal = post(base + "/calibrations", {"geometry_sha256": sha, "points": [ref(0), ref(1)],
                  "known_length": 200, "unit": "mm", "source_note": "Authored analytic width, not a field measurement.", "label": "Analytic reference A–B"})
        calibration_ms = (time.perf_counter() - start)*1000
        rows = []
        # Existing dense face indices encode an independent 120 mm depth check at x=-1,y=0.
        for label, pair, actual in [("height (10% anisotropic stretch)", [0, 2], 300),
                                    ("depth (unchanged)", [4, 5], 120)]:
            for scale, cal_id in [("relative", None), ("reference_calibrated", cal["id"])]:
                body = {"geometry_sha256": sha, "points": [ref(i) for i in pair], "label": label}
                if cal_id: body.update(calibration_id=cal_id, validation={"known_length": actual, "unit": "mm", "source_note": "Independent authored dimension; not fitted and not a field measurement."})
                start = time.perf_counter()
                result = post(base, body)
                rows.append({"label": label, "scale": scale, "distance_units": result["distance_units"],
                    "distance_mm": result["distance_mm"], "validation": result["validation"], "api_roundtrip_ms": (time.perf_counter()-start)*1000})
        report = {"scope": "analytic only; no field/model accuracy claim", "job_id": job_id, "geometry_sha256": sha,
                  "calibration_api_ms": calibration_ms, "cold_warm_scope": "model-free local TestClient; includes GLB parsing and SQLite; excludes browser/upload/ML", "checks": rows}
        (data_dir / "analytic-evaluation.json").write_text(json.dumps(report, indent=2))
        (data_dir / "measurement-receipt.json").write_text(json.dumps(client.get(base).json(), indent=2))
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/measurement-demo"))
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    manifest = build_demo(data_dir)
    if args.evaluate:
        report = evaluate(data_dir, manifest)
        for row in report["checks"]:
            error = row["validation"]["relative_error_pct"] if row["validation"] else None
            print(f"{row['scale']}: {row['label']}: {row['distance_mm']} mm, error={error}%")
    print(f"Job ID: {manifest['job_id']}")
    print(f"PV3D_DATA_DIR={data_dir} .venv/bin/python -m uvicorn pv3d.app:create_app --factory --host 127.0.0.1 --port 8000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
