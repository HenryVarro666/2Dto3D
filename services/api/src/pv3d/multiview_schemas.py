"""Multiview contracts kept separate from the backward-compatible single-photo API."""

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from .schemas import Asset, Category, Contract, Detection, Identifier, ManualComponent, Status, Vector3

ResourceId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class CaptureCreate(Contract):
    asset_ids: list[ResourceId] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def unique_assets(self):
        if len(set(self.asset_ids)) != len(self.asset_ids):
            raise ValueError("Each capture view must be a different photo")
        return self


class Capture(Contract):
    id: ResourceId
    assets: list[Asset]
    created_at: str


class ViewInput(ManualComponent):
    id: Identifier
    asset_id: ResourceId
    component_id: Identifier | None = None


class ViewObservation(Detection):
    id: Identifier
    asset_id: ResourceId
    component_id: Identifier


class MultiComponent(Contract):
    id: Identifier
    category: Category
    label: str
    source: Literal["grounding_dino", "manual"]
    score: float | None
    observation_ids: list[Identifier]
    point_count: int = Field(ge=0)
    color: str
    position: Vector3
    dimensions: Vector3


class MultiJobRequest(Contract):
    capture_id: ResourceId
    mode: Literal["automatic", "manual"] = "automatic"
    observations: list[ViewInput] | None = Field(default=None, max_length=200)
    base_job_id: ResourceId | None = None

    @model_validator(mode="after")
    def validate_mode(self):
        if self.mode == "automatic" and (self.observations is not None or self.base_job_id):
            raise ValueError("Automatic capture jobs cannot include manual observations or a base job")
        if self.mode == "manual" and (self.observations is None or self.base_job_id is None):
            raise ValueError("Manual capture jobs require observations and a completed base job")
        ids = [item.id for item in self.observations or []]
        if len(ids) != len(set(ids)):
            raise ValueError("Observation IDs must be unique")
        return self


class MultiResult(Contract):
    job_id: ResourceId
    capture_id: ResourceId
    geometry_job_id: ResourceId
    representation: Literal["fused_point_cloud"] = "fused_point_cloud"
    metric_scale_status: Literal["unknown"] = "unknown"
    views: list[Asset]
    observations: list[ViewObservation]
    components: list[MultiComponent]
    scene_url: str | None
    ply_url: str | None
    json_url: str
    point_count: int = Field(ge=0)
    context_point_count: int = Field(ge=0)
    model: dict[str, Any]
    quality: dict[str, Any]
    timings: dict[str, float]
    warnings: list[str]


class MultiJob(Contract):
    id: ResourceId
    capture_id: ResourceId
    status: Status
    stage: str
    view_index: int = Field(ge=0)
    total_views: int = Field(ge=2, le=8)
    created_at: str
    elapsed_ms: float
    error: str | None
    result: MultiResult | None
