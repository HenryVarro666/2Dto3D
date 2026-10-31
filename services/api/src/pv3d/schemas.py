"""Validated public contracts shared by the HTTP and geometry boundaries."""

import math
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Category = Literal["cabinet", "bracket", "pole", "cables", "connector", "cable_tray", "unknown"]
SceneMode = Literal["single", "multiple"]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")]
BBox = tuple[float, float, float, float]
Vector3 = tuple[float, float, float]
Status = Literal["queued", "running", "succeeded", "needs_review", "failed", "interrupted"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ManualComponent(Contract):
    id: Identifier | None = None
    category: Category
    label: str = Field(min_length=1, max_length=160)
    bbox: BBox
    refinement_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")] | None = None

    @field_validator("label")
    @classmethod
    def nonempty_label(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Label must contain visible text")
        return value

    @field_validator("bbox")
    @classmethod
    def normalized_bbox(cls, value):
        x1, y1, x2, y2 = value
        if not all(math.isfinite(v) for v in value) or not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("bbox must have positive area within the normalized image")
        return value


class Detection(ManualComponent):
    score: float | None = Field(default=None, ge=0, le=1)
    source: Literal["grounding_dino", "manual"] = "grounding_dino"
    mask_polygon: list[tuple[float, float]] | None = None
    mask_polygons: list[list[tuple[float, float]]] | None = Field(default=None, max_length=64)
    mask_model: dict[str, Any] | None = None

    @field_validator("mask_polygon")
    @classmethod
    def normalized_polygon(cls, value):
        if value is not None and (
            len(value) < 3 or any(not all(math.isfinite(v) and 0 <= v <= 1 for v in point) for point in value)
        ):
            raise ValueError("mask polygon must contain at least three normalized points")
        return value

    @field_validator("mask_polygons")
    @classmethod
    def normalized_polygons(cls, value):
        if value is not None:
            for ring in value:
                if len(ring) > 128:
                    raise ValueError("mask ring exceeds 128 points")
                cls.normalized_polygon(ring)
        return value


class PointPrompt(Contract):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    label: Literal[0, 1]


class RefinementRequest(Contract):
    asset_id: str = Field(min_length=1, max_length=128)
    bbox: BBox
    points: list[PointPrompt] = Field(default_factory=list, max_length=64)

    @field_validator("bbox")
    @classmethod
    def normalized_bbox(cls, value):
        return ManualComponent.normalized_bbox(value)

    @model_validator(mode="after")
    def positive_points_inside_box(self):
        x1, y1, x2, y2 = self.bbox
        if any(p.label == 1 and not (x1 <= p.x <= x2 and y1 <= p.y <= y2) for p in self.points):
            raise ValueError("positive points must be inside the prompt box")
        return self


class Refinement(Contract):
    id: str
    asset_id: str
    bbox: BBox
    geometry_bbox: BBox
    points: list[PointPrompt]
    mask_polygons: list[list[tuple[float, float]]]
    mask_url: str
    model: dict[str, Any]
    timings: dict[str, float]
    warnings: list[str] = Field(default_factory=list)


class JobRequest(Contract):
    asset_id: str = Field(min_length=1, max_length=128)
    mode: Literal["automatic", "manual"] = "automatic"
    scene_mode: SceneMode = "single"
    components: list[ManualComponent] | None = Field(default=None, max_length=100)
    base_job_id: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_mode(self):
        if self.mode == "automatic" and self.components is not None:
            raise ValueError("components require explicit manual mode")
        if self.mode == "automatic" and self.base_job_id is not None:
            raise ValueError("base_job_id requires explicit manual mode")
        if self.mode == "manual" and self.components is None:
            raise ValueError("manual mode requires components")
        ids = [c.id for c in self.components or [] if c.id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError("component IDs must be unique")
        return self


class Asset(Contract):
    id: str
    width: int
    height: int
    image_url: str
    sha256: str


class Component(Detection):
    id: Identifier
    primitive: Literal["box", "cylinder", "cable_bundle"]
    color: str
    position: Vector3
    dimensions: Vector3
    node_name: str


class Result(Contract):
    job_id: str
    asset_id: str
    equipment_type: Literal["string_inverter"] = "string_inverter"
    scene_mode: SceneMode = "single"
    representation: Literal["structural_schematic"] = "structural_schematic"
    metric_scale_status: Literal["unknown"] = "unknown"
    components: list[Component]
    scene_url: str | None
    json_url: str
    warnings: list[str]
    model: dict[str, Any]
    timings: dict[str, float]


class Job(Contract):
    id: str
    asset_id: str
    status: Status
    stage: str
    created_at: str
    elapsed_ms: float
    error: str | None
    result: Result | None
