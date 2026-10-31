"""Immutable scale receipts over exported GLB points; never over display transforms."""
import hashlib
import io
import math
import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

import numpy as np
import trimesh
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import Field, model_validator

from .schemas import Contract, Identifier

Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Unit = Literal["mm", "cm", "m"]
ResourceId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
UNITS = {"mm": 1.0, "cm": 10.0, "m": 1000.0}


class PointRef(Contract):
    component_id: Identifier | Literal["__context__"]
    point_index: int = Field(ge=0, strict=True)


class KnownLength(Contract):
    known_length: float = Field(ge=0.000001, le=1_000_000, allow_inf_nan=False)
    unit: Unit
    source_note: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def meaningful_source(self):
        self.source_note = self.source_note.strip()
        if not self.source_note:
            raise ValueError("MEASUREMENT_SOURCE_REQUIRED")
        return self


class SegmentRequest(Contract):
    geometry_sha256: Hash
    points: tuple[PointRef, PointRef]
    label: str = Field(default="", max_length=160)


class CalibrationRequest(SegmentRequest, KnownLength):
    pass


class MeasurementRequest(SegmentRequest):
    calibration_id: ResourceId | None = None
    validation: KnownLength | None = None

    @model_validator(mode="after")
    def validation_requires_calibration(self):
        if self.validation is not None and self.calibration_id is None:
            raise ValueError("MEASUREMENT_CALIBRATION_REQUIRED")
        return self


def geometry(store, identifier, expected_sha=None):
    job = store.get_multiview_job(identifier) if re.fullmatch(r"[a-f0-9]{32}", identifier) else None
    if job is None:
        raise HTTPException(404, "MEASUREMENT_JOB_NOT_FOUND")
    result = job.get("result") or {}
    if (job["status"] not in {"succeeded", "needs_review"} or not result.get("scene_url")
            or result.get("representation") != "fused_point_cloud"):
        raise HTTPException(409, "MEASUREMENT_GEOMETRY_UNAVAILABLE")
    path = store.data_dir / "multiview" / identifier / "cloud.glb"
    if not path.is_file():
        raise HTTPException(409, "MEASUREMENT_GEOMETRY_UNAVAILABLE")
    raw = path.read_bytes()
    fingerprint = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and fingerprint != expected_sha:
        raise HTTPException(409, "MEASUREMENT_GEOMETRY_CHANGED")
    return result, raw, fingerprint


def resolve_segment(raw, result, points):
    """process=False preserves GLB POSITION order, including duplicate vertices."""
    scene = trimesh.load(io.BytesIO(raw), file_type="glb", force="scene", process=False)
    allowed = {c["id"] for c in result["components"]} | {"__context__"}
    resolved = []
    for ref in points:
        if ref.component_id not in allowed or ref.component_id not in scene.graph.nodes_geometry:
            raise HTTPException(422, "MEASUREMENT_POINT_INVALID")
        transform, geometry_name = scene.graph[ref.component_id]
        cloud = scene.geometry[geometry_name]
        if not isinstance(cloud, trimesh.points.PointCloud) or ref.point_index >= len(cloud.vertices):
            raise HTTPException(422, "MEASUREMENT_POINT_INVALID")
        vertex = cloud.vertices[ref.point_index]
        position = trimesh.transform_points(vertex[None, :], transform)[0]
        if not np.isfinite(position).all():
            raise HTTPException(422, "MEASUREMENT_POINT_INVALID")
        resolved.append({**ref.model_dump(), "position": position.tolist()})
    distance = float(np.linalg.norm(np.array(resolved[0]["position"]) - resolved[1]["position"]))
    if not math.isfinite(distance) or distance <= 1e-12:
        raise HTTPException(422, "MEASUREMENT_POINTS_TOO_CLOSE")
    return resolved, distance


def same_segment(first, second):
    a, b = (np.array(p["position"]) for p in first)
    c, d = (np.array(p["position"]) for p in second)
    # Float32 GLB coordinates are canonical. Absolute tolerance avoids rejecting a merely nearby check.
    return ((np.allclose(a, c, rtol=0, atol=1e-9) and np.allclose(b, d, rtol=0, atol=1e-9))
            or (np.allclose(a, d, rtol=0, atol=1e-9) and np.allclose(b, c, rtol=0, atol=1e-9)))


def _base(identifier, result, fingerprint, request, resolved, distance):
    return {"id": uuid4().hex, "job_id": identifier, "geometry_job_id": result["geometry_job_id"],
            "geometry_sha256": fingerprint, "coordinate_frame": "GLB world, Y-up, un-exploded",
            "points": resolved, "distance_units": distance, "label": request.label.strip(),
            "created_at": datetime.now(UTC).isoformat()}


def register_measurement_routes(app):
    def session(identifier):
        store = app.state.store
        result, _, fingerprint = geometry(store, identifier)
        records = store.get_measurement_records(identifier)
        return {"schema_version": 1, "job_id": identifier, "geometry_job_id": result["geometry_job_id"],
                "geometry_sha256": fingerprint, "raw_geometry_scale_status": "unknown",
                "calibrations": [r for kind, r in records if kind == "calibration"],
                "measurements": [r for kind, r in records if kind == "measurement"],
                "stale_record_count": sum(r["geometry_sha256"] != fingerprint for _, r in records)}

    @app.get("/api/multiview/jobs/{identifier}/measurements")
    def get_session(identifier: str):
        return session(identifier)

    @app.get("/api/multiview/jobs/{identifier}/measurements/export.json")
    def export_session(identifier: str):
        return JSONResponse(session(identifier), headers={
            "Content-Disposition": f'attachment; filename="{identifier}-measurements.json"'})

    @app.post("/api/multiview/jobs/{identifier}/measurements/calibrations", status_code=201)
    def calibrate(identifier: str, request: CalibrationRequest):
        store = app.state.store
        result, raw, fingerprint = geometry(store, identifier, request.geometry_sha256)
        resolved, distance = resolve_segment(raw, result, request.points)
        known_mm = request.known_length * UNITS[request.unit]
        record = {**_base(identifier, result, fingerprint, request, resolved, distance),
                  "scale_status": "reference_calibrated", **request.model_dump(include={
                      "known_length", "unit", "source_note"}),
                  "known_length_mm": known_mm, "mm_per_unit": known_mm / distance,
                  "reference_kind": "user_supplied"}
        store.add_measurement_record(identifier, "calibration", record)
        return record

    @app.post("/api/multiview/jobs/{identifier}/measurements", status_code=201)
    def measure(identifier: str, request: MeasurementRequest):
        store = app.state.store
        result, raw, fingerprint = geometry(store, identifier, request.geometry_sha256)
        resolved, distance = resolve_segment(raw, result, request.points)
        calibration = None
        if request.calibration_id:
            calibration = next((r for kind, r in store.get_measurement_records(identifier)
                                if kind == "calibration" and r["id"] == request.calibration_id), None)
            if calibration is None or calibration["geometry_sha256"] != fingerprint:
                raise HTTPException(422, "MEASUREMENT_CALIBRATION_MISMATCH")
        record = {**_base(identifier, result, fingerprint, request, resolved, distance),
                  "scale_status": "reference_calibrated" if calibration else "relative_estimate",
                  "calibration_id": request.calibration_id,
                  "distance_mm": distance * calibration["mm_per_unit"] if calibration else None,
                  "validation": None}
        if request.validation:
            if same_segment(resolved, calibration["points"]):
                raise HTTPException(422, "MEASUREMENT_REFERENCE_REUSED")
            known_mm = request.validation.known_length * UNITS[request.validation.unit]
            error = record["distance_mm"] - known_mm
            record["validation"] = {**request.validation.model_dump(), "known_length_mm": known_mm,
                                    "absolute_error_mm": abs(error), "signed_error_mm": error,
                                    "relative_error_pct": abs(error) / known_mm * 100,
                                    "reference_kind": "user_supplied", "used_for_calibration": False}
        store.add_measurement_record(identifier, "measurement", record)
        return record
