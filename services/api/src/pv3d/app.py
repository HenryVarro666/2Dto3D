"""Local FastAPI boundary for durable photo recognition and schematic jobs."""

import hashlib
import io
import json
import logging
import re
import shutil
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from . import __version__
from .auth import TokenAuthMiddleware, register_session_routes
from .config import DEFAULT_MAX_PENDING_JOBS, Settings
from .geometry import build_components, export_scene
from .manual import apply_manual_components
from .multiview_schemas import MultiResult
from .observability import BodyLimitMiddleware, RequestContextMiddleware
from .refinement import EmptyRegionError, save_refinement
from .schemas import Asset, Job, JobRequest, Refinement, RefinementRequest, Result
from .store import DataDirectoryLock, Store

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[4]
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MULTIPART_OVERHEAD_BYTES = 64 * 1024  # Boundary and field headers around the 20 MB file part.
MAX_IMAGE_PIXELS = 25_000_000
MAX_IMAGE_EDGE = 2048
MAX_PENDING_JOBS = DEFAULT_MAX_PENDING_JOBS
QUEUE_FULL = "The local processing queue is full. Retry after a task finishes."
SHUTTING_DOWN = "The service is shutting down. Retry after it restarts."
WORKER_BUSY = "The inference worker is busy with a long task. Retry the refinement later."
# Pillow reports multi-picture JPEGs (phone depth/3D captures) as MPO; the primary frame decodes as JPEG.
UPLOAD_FORMATS = frozenset({"JPEG", "MPO", "PNG", "WEBP"})
RESOURCE_ID = re.compile(r"^[a-f0-9]{32}$")


def _normalized_image(content: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as probe:
                if probe.format not in UPLOAD_FORMATS:
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
    """One inference thread, a bounded admission queue and durable job records."""

    def __init__(
        self,
        store: Store,
        detector,
        reconstructor=None,
        max_pending: int = MAX_PENDING_JOBS,
        refine_timeout_s: float = 300.0,
    ):
        if max_pending < 1:
            raise ValueError("max_pending must be at least 1")
        if not refine_timeout_s > 0:
            raise ValueError("refine_timeout_s must be positive")
        self.store = store
        self.detector = detector
        self.reconstructor = reconstructor
        self.max_pending = max_pending
        self.refine_timeout_s = refine_timeout_s
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pv3d-worker")
        self.capacity = threading.BoundedSemaphore(max_pending)
        self._slots_lock = threading.Lock()
        self._in_flight = 0
        self._closed = False

    def _acquire_slot(self):
        if self._closed:
            raise HTTPException(503, SHUTTING_DOWN)
        if not self.capacity.acquire(blocking=False):
            raise HTTPException(409, QUEUE_FULL)
        with self._slots_lock:
            self._in_flight += 1

    def _release_slot(self):
        with self._slots_lock:
            self._in_flight -= 1
        self.capacity.release()

    def _schedule(self, function, *args):
        """Hand work to the single worker; a closed executor is a 503, not a 500."""
        try:
            return self.executor.submit(function, *args)
        except RuntimeError as error:
            raise HTTPException(503, SHUTTING_DOWN) from error

    def queue_status(self) -> dict:
        with self._slots_lock:
            in_flight = self._in_flight
        return {"max_pending": self.max_pending, "in_flight": in_flight,
                "available": max(0, self.max_pending - in_flight)}

    def submit(self, request: JobRequest):
        self._acquire_slot()
        try:
            job = self.store.create_job(request.asset_id)
            self._schedule(self._run, job, request)
            return job
        except Exception:
            self._release_slot()
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
        self._acquire_slot()
        try:
            job = self.store.create_multiview_job(request.capture_id, total_views)
            self._schedule(self._run_multiview, job, request)
            return job
        except Exception:
            self._release_slot()
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
            self._release_slot()

    def refine(self, request):
        """Interactive refinement waits behind the single worker, but never indefinitely."""
        self._acquire_slot()
        try:
            future = self._schedule(self._refine, request)
        except Exception:
            self._release_slot()
            raise
        try:
            return future.result(timeout=self.refine_timeout_s)
        except FutureTimeoutError:
            if future.cancel():
                # Never started: the worker is still busy with an earlier task. Free the slot now;
                # a started task releases its own slot when it finishes.
                self._release_slot()
            raise HTTPException(503, WORKER_BUSY) from None

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
            self._release_slot()

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
            result = Result.model_validate(
                {
                    "job_id": job_id,
                    "asset_id": asset["id"],
                    "scene_mode": request.scene_mode,
                    "components": components,
                    "scene_url": f"/api/jobs/{job_id}/scene.glb" if components else None,
                    "json_url": f"/api/jobs/{job_id}/result.json",
                    "warnings": list(dict.fromkeys([*recognition.get("warnings", []), *geometry_warnings])),
                    "model": recognition.get("model", {}),
                    "timings": {
                        **recognition.get("timings", {}),
                        "geometry_ms": (time.perf_counter() - geometry_started) * 1000,
                        "processing_ms": elapsed,
                    },
                }
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
            self._release_slot()

    def close(self):
        """Finish the running task, drop queued ones and record them as interrupted."""
        self._closed = True
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.store.interrupt_unfinished()


def create_app(
    data_dir: Path | None = None, detector=None, reconstructor=None, settings: Settings | None = None
) -> FastAPI:
    """Create an isolated service; only the slow model boundary is injectable for tests."""
    settings = Settings.from_env() if settings is None else settings
    configured_dir = Path(data_dir or settings.data_dir).resolve()
    if reconstructor is None:
        from .reconstruction import VggtReconstructor

        reconstructor = VggtReconstructor(timeout_s=settings.multiview_timeout_s)
    if detector is None:
        from .perception import GroundingDetector

        detector = GroundingDetector(cache_dir=Path(settings.model_dir), device=settings.device)

    @asynccontextmanager
    async def lifespan(application):
        # One live server per data directory; a second one would rewrite this one's job states.
        with DataDirectoryLock(configured_dir):
            store = Store(configured_dir)
            store.interrupt_unfinished()
            runner = JobRunner(
                store,
                detector,
                reconstructor,
                max_pending=settings.max_pending_jobs,
                refine_timeout_s=settings.refine_timeout_s,
            )
            application.state.store = store
            application.state.runner = runner
            try:
                yield
            finally:
                runner.close()

    application = FastAPI(title="PV Component Schematic Workbench", version=__version__, lifespan=lifespan)
    if settings.api_token:
        # Innermost: runs after request context and body limits, before any route or body parsing.
        application.add_middleware(TokenAuthMiddleware, token=settings.api_token)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        BodyLimitMiddleware, limits={"/api/assets": MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES}
    )
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
            max_age=600,
        )

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
        path = configured_dir / "refinements" / ref["id"] / "mask.png"
        if not path.is_file():
            raise HTTPException(404, "The refinement mask is unavailable.")
        return FileResponse(path, media_type="image/png")

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
        return {
            "status": "ok",
            "version": __version__,
            "authentication": "token" if settings.api_token else "none",
            "model": model_status,
            "multiview": reconstructor.status(),
            "queue": application.state.runner.queue_status(),
        }

    def _store_asset(content: bytes) -> dict:
        """CPU and disk work for one upload; runs in a worker thread, never on the event loop."""
        image = _normalized_image(content)
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
        try:
            (folder / "original.bin").write_bytes(content)
            image.save(folder / "image.jpg", format="JPEG", quality=94)
            application.state.store.add_asset(asset)
        except Exception:
            # Never leave files that no ledger row references.
            shutil.rmtree(folder, ignore_errors=True)
            raise
        return asset

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
        return await run_in_threadpool(_store_asset, bytes(content))

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

    if settings.api_token:
        register_session_routes(application, settings.api_token, settings.session_max_age_s)

    # Prevent unknown API URLs from falling through into the optional web app.
    from .captures import register_capture_routes
    from .measurement import register_measurement_routes

    register_measurement_routes(application)
    register_capture_routes(application, configured_dir, require_asset, require_refinement)

    # Only the methods the API uses: a wrong method on a real route then reports 405, not 404.
    @application.api_route("/api/{unmatched:path}", methods=["GET", "POST"])
    def unknown_api(unmatched: str):
        raise HTTPException(404, "API route not found.")

    web_dist = ROOT / "apps" / "web" / "dist"
    if (web_dist / "index.html").is_file():
        application.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return application
