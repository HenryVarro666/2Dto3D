"""Local FastAPI boundary for durable photo recognition and schematic jobs."""

import hashlib
import io
import json
import logging
import os
import re
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError

from .geometry import build_components, export_scene
from .manual import apply_manual_components
from .multiview_schemas import MultiResult
from .refinement import EmptyRegionError, save_refinement
from .schemas import Asset, Job, JobRequest, Refinement, RefinementRequest, Result
from .store import Store

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[4]
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
MAX_IMAGE_EDGE = 2048
MAX_PENDING_JOBS = 8  # Includes the one running job; reject rather than grow an unbounded queue.
RESOURCE_ID = re.compile(r"^[a-f0-9]{32}$")


def _normalized_image(content: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as probe:
                if probe.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(400, "Use an actual JPEG, PNG, or WebP image.")
                if probe.width * probe.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(413, "The decoded image exceeds 25 million pixels.")
                probe.verify()
            with Image.open(io.BytesIO(content)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
                # Recreate the image so EXIF and ancillary source metadata are removed.
                return Image.frombytes("RGB", image.size, image.tobytes())
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        raise HTTPException(413, "The decoded image is too large.") from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise HTTPException(400, "The file is not a valid supported image.") from error


class JobRunner:
    def __init__(self, store: Store, detector, reconstructor=None):
        self.store = store
        self.detector = detector
        self.reconstructor = reconstructor
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pv3d-worker")
        self.capacity = threading.BoundedSemaphore(MAX_PENDING_JOBS)

    def submit(self, request: JobRequest):
        if not self.capacity.acquire(blocking=False):
            raise HTTPException(409, "The local processing queue is full. Retry after a task finishes.")
        try:
            job = self.store.create_job(request.asset_id)
            self.executor.submit(self._run, job, request)
            return job
        except Exception:
            self.capacity.release()
            raise

    def _manual_recognition(self, request):
        base_result = self.store.get_job(request.base_job_id)["result"] if request.base_job_id else None
        previous = (
            {component["id"]: component for component in base_result["components"]} if base_result else {}
        )
        detections = apply_manual_components(request.components, previous, self.store)
        return {
            "detections": detections,
            "model": {
                "mode": "manual",
                "model_id": None,
                **(
                    {"base_job_id": request.base_job_id, "base_model": base_result["model"]}
                    if base_result
                    else {}
                ),
            },
            "warnings": [
                "Manual edits were applied. Unchanged component evidence is retained from the base result."
            ],
            "timings": {},
        }

    def submit_multiview(self, request, total_views):
        if not self.capacity.acquire(blocking=False):
            raise HTTPException(409, "The local processing queue is full. Retry after a task finishes.")
        try:
            job = self.store.create_multiview_job(request.capture_id, total_views)
            self.executor.submit(self._run_multiview, job, request)
            return job
        except Exception:
            self.capacity.release()
            raise

    def _run_multiview(self, job, request):
        started = time.perf_counter()
        current_stage = "starting"

        def report(stage, view_index=0):
            nonlocal current_stage
            current_stage = stage
            self.store.update_multiview_job(
                job["id"],
                status="running",
                stage=stage,
                view_index=view_index,
                elapsed_ms=(time.perf_counter() - started) * 1000,
            )

        try:
            report("manual_components" if request.mode == "manual" else "starting")
            from .multiview_runner import run_multiview

            result = MultiResult.model_validate(
                run_multiview(self.store, self.detector, self.reconstructor, job, request, report)
            ).model_dump(mode="json")
            folder = self.store.data_dir / "multiview" / job["id"]
            folder.mkdir(parents=True, exist_ok=True)
            temporary = folder / "result.tmp"
            temporary.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            temporary.replace(folder / "result.json")
            ready = bool(
                result["point_count"] and result["components"] and not result["quality"].get("needs_review")
            )
            self.store.update_multiview_job(
                job["id"],
                status="succeeded" if ready else "needs_review",
                stage="complete",
                elapsed_ms=(time.perf_counter() - started) * 1000,
                result=result,
            )
        except Exception:
            log.exception("Multi-view job %s failed", job["id"])
            self.store.update_multiview_job(
                job["id"],
                status="failed",
                stage=current_stage,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                error="Multi-view processing failed. Check local model setup, retry, or return to single-photo mode.",
            )
        finally:
            self.capacity.release()

    def refine(self, request):
        if not self.capacity.acquire(blocking=False):
            raise HTTPException(409, "The local processing queue is full. Retry after a task finishes.")
        try:
            future = self.executor.submit(self._refine, request)
        except Exception:
            self.capacity.release()
            raise
        return future.result()

    def _refine(self, request):
        try:
            asset = self.store.get_asset(request.asset_id)
            with Image.open(self.store.data_dir / "assets" / asset["id"] / "image.jpg") as source:
                prediction = self.detector.refine(
                    source.convert("RGB"),
                    request.bbox,
                    [point.model_dump() for point in request.points],
                    cache_key=asset["id"] + asset["sha256"],
                )
            result = save_refinement(self.store.data_dir, asset, request, prediction)
            self.store.add_refinement(result)
            return result
        finally:
            self.capacity.release()

    def _run(self, job, request):
        started = time.perf_counter()
        job_id = job["id"]
        current_stage = "manual_components" if request.mode == "manual" else "starting"

        def report(stage):
            nonlocal current_stage
            current_stage = stage
            self.store.update_job(
                job_id, status="running", stage=stage, elapsed_ms=(time.perf_counter() - started) * 1000
            )

        try:
            report(current_stage)
            asset = self.store.get_asset(job["asset_id"])
            if request.mode == "manual":
                recognition = self._manual_recognition(request)
            else:
                with Image.open(self.store.data_dir / "assets" / asset["id"] / "image.jpg") as source:
                    recognition = self.detector.detect(
                        source.convert("RGB"), on_progress=report, scene_mode=request.scene_mode
                    )
            report("geometry")
            geometry_started = time.perf_counter()
            components, geometry_warnings = build_components(
                recognition["detections"],
                image_size=(asset["width"], asset["height"]),
            )
            folder = self.store.data_dir / "jobs" / job_id
            folder.mkdir(parents=True, exist_ok=True)
            if components:
                report("exporting")
                export_scene(components, folder / "scene.glb")
            elapsed = (time.perf_counter() - started) * 1000
            result = Result(
                job_id=job_id,
                asset_id=asset["id"],
                scene_mode=request.scene_mode,
                components=components,
                scene_url=f"/api/jobs/{job_id}/scene.glb" if components else None,
                json_url=f"/api/jobs/{job_id}/result.json",
                warnings=list(dict.fromkeys([*recognition.get("warnings", []), *geometry_warnings])),
                model=recognition.get("model", {}),
                timings={
                    **recognition.get("timings", {}),
                    "geometry_ms": (time.perf_counter() - geometry_started) * 1000,
                    "processing_ms": elapsed,
                },
            ).model_dump(mode="json")
            temporary = folder / "result.tmp"
            temporary.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            temporary.replace(folder / "result.json")
            self.store.update_job(
                job_id,
                status="succeeded" if components else "needs_review",
                stage="complete",
                elapsed_ms=elapsed,
                result=result,
            )
        except Exception:
            log.exception("Job %s failed", job_id)
            self.store.update_job(
                job_id,
                status="failed",
                stage=current_stage,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                error="Processing failed. Check local server logs, retry, or use manual components.",
            )
        finally:
            self.capacity.release()

    def close(self):
        self.executor.shutdown(wait=True)


def create_app(data_dir: Path | None = None, detector=None, reconstructor=None) -> FastAPI:
    """Create an isolated service; only the slow model boundary is injectable for tests."""
    configured_dir = Path(data_dir or os.environ.get("PV3D_DATA_DIR", ROOT / "data" / "runtime")).resolve()
    if reconstructor is None:
        from .reconstruction import VggtReconstructor

        reconstructor = VggtReconstructor()
    if detector is None:
        from .perception import GroundingDetector

        detector = GroundingDetector(
            cache_dir=Path(os.environ.get("PV3D_MODEL_DIR", ROOT / "models" / "huggingface")),
            device=os.environ.get("PV3D_DEVICE", "auto"),
        )

    @asynccontextmanager
    async def lifespan(application):
        store = Store(configured_dir)
        store.interrupt_unfinished()
        runner = JobRunner(store, detector, reconstructor)
        application.state.store = store
        application.state.runner = runner
        try:
            yield
        finally:
            runner.close()

    application = FastAPI(title="PV Component Schematic Workbench", version="3.0.0", lifespan=lifespan)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(_request, error):
        # Do not echo raw input: NaN cannot be JSON-encoded, and body values may be sensitive.
        details = [
            {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]} for item in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": details})

    def require_asset(identifier):
        asset = application.state.store.get_asset(identifier) if RESOURCE_ID.fullmatch(identifier) else None
        if asset is None:
            raise HTTPException(404, "Asset not found.")
        return asset

    def require_job(identifier):
        job = application.state.store.get_job(identifier) if RESOURCE_ID.fullmatch(identifier) else None
        if job is None:
            raise HTTPException(404, "Job not found.")
        return job

    def require_result(identifier):
        job = require_job(identifier)
        if job["status"] not in {"succeeded", "needs_review"} or job["result"] is None:
            raise HTTPException(409, "The job has no completed result.")
        return job["result"]

    def require_refinement(identifier):
        result = (
            application.state.store.get_refinement(identifier) if RESOURCE_ID.fullmatch(identifier) else None
        )
        if result is None:
            raise HTTPException(404, "Refinement not found.")
        return result

    @application.post("/api/refinements", response_model=Refinement, status_code=201)
    def refine_component(request: RefinementRequest):
        require_asset(request.asset_id)
        try:
            return application.state.runner.refine(request)
        except HTTPException:
            raise
        except EmptyRegionError as error:
            raise HTTPException(
                422, "No usable region. Add points, redraw the box, or use the box without refinement."
            ) from error
        except Exception as error:
            log.exception("Boundary refinement failed")
            raise HTTPException(
                503, "Boundary refinement failed. Retry or keep the box without refinement."
            ) from error

    @application.get("/api/refinements/{identifier}/mask.png")
    def get_refinement_mask(identifier: str):
        ref = require_refinement(identifier)
        return FileResponse(configured_dir / "refinements" / ref["id"] / "mask.png", media_type="image/png")

    @application.get("/api/health")
    def health():
        try:
            model_status = dict(detector.status())
            if model_status.get("error"):
                model_status["error"] = "Model unavailable. Check local server logs."
        except Exception:
            log.exception("Model status failed")
            model_status = {
                "state": "failed",
                "model_id": None,
                "device": "unknown",
                "error": "Model status unavailable.",
            }
        return {"status": "ok", "model": model_status, "multiview": reconstructor.status()}

    @application.post("/api/assets", response_model=Asset, status_code=201)
    async def upload_asset(file: Annotated[UploadFile, File()]):
        content = bytearray()
        try:
            while chunk := await file.read(1024 * 1024):
                content.extend(chunk)
                if len(content) > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "The upload exceeds 20 MB.")
        finally:
            await file.close()
        image = _normalized_image(bytes(content))
        identifier = uuid4().hex
        asset = {
            "id": identifier,
            "width": image.width,
            "height": image.height,
            "image_url": f"/api/assets/{identifier}/image",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        folder = configured_dir / "assets" / identifier
        folder.mkdir(parents=True)
        (folder / "original.bin").write_bytes(content)
        image.save(folder / "image.jpg", format="JPEG", quality=94)
        application.state.store.add_asset(asset)
        return asset

    @application.get("/api/assets/{identifier}/image")
    def get_image(identifier: str):
        asset = require_asset(identifier)
        path = configured_dir / "assets" / asset["id"] / "image.jpg"
        if not path.is_file():
            raise HTTPException(404, "The asset image is unavailable.")
        return FileResponse(path, media_type="image/jpeg")

    @application.post("/api/jobs", response_model=Job, status_code=202)
    def start_job(request: JobRequest):
        require_asset(request.asset_id)
        for component in request.components or []:
            if component.refinement_id:
                ref = require_refinement(component.refinement_id)
                if ref["asset_id"] != request.asset_id or list(component.bbox) != ref["geometry_bbox"]:
                    raise HTTPException(400, "Refinement must match the image and component box.")
        if request.base_job_id is not None:
            base = require_job(request.base_job_id)
            if base["asset_id"] != request.asset_id:
                raise HTTPException(400, "The base job must belong to the same image asset.")
            require_result(request.base_job_id)
        return application.state.runner.submit(request)

    @application.get("/api/jobs/{identifier}", response_model=Job)
    def get_job(identifier: str):
        return require_job(identifier)

    @application.get("/api/jobs/{identifier}/result", response_model=Result)
    def get_result(identifier: str):
        return require_result(identifier)

    @application.get("/api/jobs/{identifier}/result.json")
    def get_result_json(identifier: str):
        require_result(identifier)
        path = configured_dir / "jobs" / identifier / "result.json"
        if not path.is_file():
            raise HTTPException(409, "The result file is unavailable. Start a new task.")
        return FileResponse(path, media_type="application/json", filename=f"{identifier}-result.json")

    @application.get("/api/jobs/{identifier}/scene.glb")
    def get_scene(identifier: str):
        result = require_result(identifier)
        path = configured_dir / "jobs" / identifier / "scene.glb"
        if result["scene_url"] is None or not path.is_file():
            raise HTTPException(409, "There is no component scene. Add or correct components manually.")
        return FileResponse(path, media_type="model/gltf-binary", filename=f"{identifier}-scene.glb")

    # Prevent unknown API URLs from falling through into the optional web app.
    from .captures import register_capture_routes
    from .measurement import register_measurement_routes

    register_measurement_routes(application)
    register_capture_routes(application, configured_dir, require_asset, require_refinement)

    @application.api_route(
        "/api/{unmatched:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    def unknown_api(unmatched: str):
        raise HTTPException(404, "API route not found.")

    web_dist = ROOT / "apps" / "web" / "dist"
    if (web_dist / "index.html").is_file():
        application.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return application
