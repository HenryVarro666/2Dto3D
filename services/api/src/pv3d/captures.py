"""Capture resources and ownership validation; inference remains on the shared runner."""

import re

from fastapi import HTTPException
from fastapi.responses import FileResponse

from .multiview_schemas import Capture, CaptureCreate, MultiJob, MultiJobRequest, MultiResult

RESOURCE_ID = re.compile(r"^[a-f0-9]{32}$")


def register_capture_routes(app, data_dir, require_asset, require_refinement):
    def require_capture(identifier):
        result = app.state.store.get_capture(identifier) if RESOURCE_ID.fullmatch(identifier) else None
        if result is None:
            raise HTTPException(404, "Capture not found.")
        return result

    def require_job(identifier):
        job = app.state.store.get_multiview_job(identifier) if RESOURCE_ID.fullmatch(identifier) else None
        if job is None:
            raise HTTPException(404, "Multi-view job not found.")
        return job

    def require_result(identifier):
        job = require_job(identifier)
        if job["result"] is None:
            raise HTTPException(409, "Multi-view result is not ready.")
        return job["result"]

    @app.post("/api/captures", response_model=Capture, status_code=201)
    def create_capture(request: CaptureCreate):
        assets = [require_asset(identifier) for identifier in request.asset_ids]
        if len({asset["sha256"] for asset in assets}) != len(assets):
            raise HTTPException(400, "Use different views, not repeated copies of the same photo.")
        return app.state.store.create_capture(request.asset_ids)

    @app.get("/api/captures/{identifier}", response_model=Capture)
    def get_capture(identifier: str):
        return require_capture(identifier)

    @app.post("/api/multiview/jobs", response_model=MultiJob, status_code=202)
    def start_job(request: MultiJobRequest):
        capture = require_capture(request.capture_id)
        assets = {asset["id"] for asset in capture["assets"]}
        for observation in request.observations or []:
            if observation.asset_id not in assets:
                raise HTTPException(400, "Every observation must belong to a photo in this capture.")
            if observation.refinement_id:
                ref = require_refinement(observation.refinement_id)
                if ref["asset_id"] != observation.asset_id or list(observation.bbox) != ref["geometry_bbox"]:
                    raise HTTPException(400, "Refinement must match the image and component box.")
        if request.base_job_id:
            base = require_job(request.base_job_id)
            if base["capture_id"] != request.capture_id:
                raise HTTPException(400, "The base job must belong to the same capture.")
            result = require_result(request.base_job_id)
            previous = {o["id"]: o for o in result.get("observations", [])}
            semantics: dict[str, tuple] = {}
            for observation in request.observations or []:
                old = previous.get(observation.id)
                if old and old["asset_id"] != observation.asset_id:
                    raise HTTPException(400, "An observation ID cannot move to a different photo.")
                component_id = observation.component_id or (old or {}).get("component_id")
                if component_id:
                    meaning = (observation.category, observation.label)
                    if semantics.setdefault(component_id, meaning) != meaning:
                        raise HTTPException(400, "Linked observations must use the same component name and category.")
        return app.state.runner.submit_multiview(request, len(assets))

    @app.get("/api/multiview/jobs/{identifier}", response_model=MultiJob)
    def get_job(identifier: str):
        return require_job(identifier)

    @app.get("/api/multiview/jobs/{identifier}/result.json", response_model=MultiResult)
    def get_result(identifier: str):
        return require_result(identifier)

    @app.get("/api/multiview/jobs/{identifier}/{filename}")
    def get_artifact(identifier: str, filename: str):
        result = require_result(identifier)
        fields = {
            "cloud.glb": ("scene_url", "model/gltf-binary"),
            "cloud.ply": ("ply_url", "application/octet-stream"),
        }
        if filename not in fields or not result.get(fields[filename][0]):
            raise HTTPException(404, "Point-cloud artifact not found.")
        path = data_dir / "multiview" / identifier / filename
        if not path.is_file():
            raise HTTPException(404, "Point-cloud artifact not found.")
        return FileResponse(path, media_type=fields[filename][1], filename=f"{identifier}-{filename}")
