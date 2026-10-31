"""Versioned capture jobs: immutable joint geometry, editable per-view observations."""

import json
import time
from uuid import uuid4

from PIL import Image

from .manual import apply_manual_components
from .pointcloud import build_pointcloud, export_pointcloud
from .reconstruction import load_geometry


def run_multiview(store, detector, reconstructor, job, request, report):
    assets = store.get_capture(request.capture_id)["assets"]
    folder = store.data_dir / "multiview" / job["id"]
    folder.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    recognition_models, warnings, observations = [], [], []
    if request.mode == "automatic":
        metadata = reconstructor.reconstruct(
            [store.data_dir / "assets" / a["id"] / "image.jpg" for a in assets], folder, report
        )
        geometry_id = job["id"]
        geometry_ms = (time.perf_counter() - started) * 1000
        for i, asset in enumerate(assets, 1):
            report("recognizing_view", i)
            with Image.open(store.data_dir / "assets" / asset["id"] / "image.jpg") as source:
                prediction = detector.detect(source.convert("RGB"), scene_mode="multiple",
                                             on_progress=lambda _, index=i: report("recognizing_view", index))
            recognition_models.append(prediction["model"])
            warnings.extend(prediction["warnings"])
            for detection in prediction["detections"]:
                observations.append({**detection, "id": "obs-" + uuid4().hex, "asset_id": asset["id"]})
    else:
        base = store.get_multiview_job(request.base_job_id)["result"]
        geometry_id = base["geometry_job_id"]
        geometry_ms = 0.0
        metadata = json.loads((store.data_dir / "multiview" / geometry_id / "geometry.json").read_text())
        previous = {o["id"]: o for o in base["observations"]}
        observations = apply_manual_components(request.observations, previous, store)
        for observation in observations:
            if not observation.get("component_id"):
                observation["component_id"] = previous.get(observation["id"], {}).get("component_id")
        recognition_models = base["model"].get("recognition_views", [])
        report("manual_components")
    recognition_ms = (time.perf_counter() - started) * 1000 - geometry_ms
    geometry = load_geometry(store.data_dir / "multiview" / geometry_id / "geometry.npz", len(assets))
    report("fusing")
    fusion_start = time.perf_counter()
    cloud = build_pointcloud(geometry, assets, observations, store, automatic=request.mode == "automatic")
    report("exporting")
    exported = export_pointcloud(cloud, folder)
    prefix = f"/api/multiview/jobs/{job['id']}"
    return {
        "job_id": job["id"], "capture_id": request.capture_id, "geometry_job_id": geometry_id,
        "views": assets, "observations": cloud["observations"], "components": cloud["components"],
        "scene_url": prefix + "/cloud.glb" if exported else None,
        "ply_url": prefix + "/cloud.ply" if exported else None, "json_url": prefix + "/result.json",
        "point_count": len(cloud["vertices"]), "context_point_count": cloud["context_point_count"],
        "model": {**metadata["model"], "recognition_views": recognition_models, "mode": request.mode,
                  "geometry_reused": request.mode == "manual", "base_job_id": request.base_job_id},
        "quality": cloud["quality"], "warnings": list(dict.fromkeys(warnings + cloud["warnings"])),
        "timings": {**({} if request.mode == "manual" else metadata.get("timings", {})),
                    "geometry_ms": geometry_ms, "recognition_ms": recognition_ms,
                    "fusion_export_ms": (time.perf_counter() - fusion_start) * 1000},
    }
