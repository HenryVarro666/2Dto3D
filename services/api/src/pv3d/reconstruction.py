"""Pure image geometry plus a bounded, isolated VGGT process boundary."""

import json
import os
import subprocess
import threading
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
VGGT_ID = "facebook/VGGT-1B"
VGGT_REVISION = "860abec7937da0a4c03c41d3c269c366e82abdf9"
VGGT_CODE_REVISION = "a288dd0f14786c93483e45524328726ab7b1b4ce"


def image_layout(width, height, target_size=518, resize_mode="legacy14"):
    """Separate stored raster bounds from continuous physical-photo mapping."""
    if target_size not in {224, 336, 518} or min(width, height) <= 0:
        raise ValueError("Unsupported photo dimensions or target size")
    if resize_mode not in {"legacy14", "isotropic"}:
        raise ValueError("Unsupported resize mode")
    size = np.array([width, height], dtype=float)
    scale = target_size/max(width, height)
    if resize_mode == "legacy14":
        extent = np.array([max(14, min(target_size, round(edge*scale/14)*14)) for edge in size])
        offset = (target_size-extent)//2
        rect = [*offset, *(offset+extent)]
        mapped = np.array(rect, dtype=float)
        padding, box = [0, 0], [0, 0, width, height]
    else:
        extent = size*scale
        extent[np.argmax(size)] = target_size
        offset = (target_size-extent)/2
        mapped = np.r_[offset, offset+extent]
        left = np.floor(mapped[:2]+1e-10).astype(int)
        right = np.ceil(mapped[2:]-1e-10).astype(int)
        rect = [*left, *right]
        allocated, delta = right-left, offset-left
        extra = np.maximum(delta, allocated-extent-delta)/scale
        padding = [int(np.ceil(e+2/scale))+2 if e > 1e-10 else 0 for e in extra]
        source_left = np.array(padding)-delta/scale
        box = [*source_left, *(source_left+allocated/scale)]
    return {"resize_mode": resize_mode, "source_size": [width, height], "target_size": target_size,
            "rect": list(map(int, rect)), "mapping_rect": mapped.tolist(),
            "scale_xy": ((mapped[2:]-mapped[:2])/size).tolist(),
            "source_padding": padding, "source_box": list(map(float, box))}


def prepare_images(image_paths, target_size=336, resize_mode="legacy14"):
    if not image_paths or target_size not in {224, 336, 518}:
        raise ValueError("Use photos and a supported 14-pixel-aligned input size")
    images, rects = [], []
    for path in image_paths:
        with Image.open(path) as source:
            image = source.convert("RGB")
        layout = image_layout(*image.size, target_size, resize_mode)
        left, top, right, bottom = layout["rect"]
        resized = (right-left, bottom-top)
        if resize_mode == "legacy14":
            image = image.resize(resized, Image.Resampling.BICUBIC)
        else:
            padx, pady = layout["source_padding"]
            padded = Image.new("RGB", (image.width+2*padx, image.height+2*pady), "white")
            padded.paste(image, (padx, pady))
            image = padded.resize(resized, Image.Resampling.BICUBIC,
                                  box=tuple(layout["source_box"]), reducing_gap=None)
        square = Image.new("RGB", (target_size, target_size), "white")
        square.paste(image, (left, top))
        images.append(np.asarray(square, dtype=np.float32).transpose(2, 0, 1) / 255)
        rects.append([left, top, right, bottom])
    return np.stack(images), np.asarray(rects, dtype=np.int32)


def photo_to_grid(points, rect):
    left, top, right, bottom = rect
    return np.asarray(points) * [right - left, bottom - top] + [left, top]


def load_geometry(path, view_count):
    with np.load(path, allow_pickle=False) as archive:
        data = {
            name: archive[name]
            for name in ("points", "depth", "confidence", "colors", "rects", "extrinsics", "intrinsics")
        }
    points = data["points"]
    if points.ndim != 4 or points.shape[0] != view_count or points.shape[-1] != 3:
        raise ValueError("Invalid multi-view point-map shape")
    _, height, width, _ = points.shape
    if not (0 < height <= 518 and 0 < width <= 518 and 2 <= view_count <= 8):
        raise ValueError("Invalid multi-view image dimensions")
    for name in ("depth", "confidence"):
        if data[name].shape != (view_count, height, width):
            raise ValueError("Invalid geometry map shape")
    if data["colors"].shape != points.shape or data["colors"].dtype != np.uint8:
        raise ValueError("Invalid geometry colors")
    for name, shape in (("extrinsics", (view_count, 3, 4)), ("intrinsics", (view_count, 3, 3))):
        if data[name].shape != shape or not np.isfinite(data[name]).all():
            raise ValueError("Invalid camera geometry")
    if data["rects"].shape != (view_count, 4):
        raise ValueError("Invalid photo mapping")
    for left, top, right, bottom in data["rects"]:
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError("Invalid photo mapping")
    return data


class VggtReconstructor:
    def __init__(self, runtime_python=None, worker_script=None, cache_dir=None, device=None, input_size=None,
                 resize_mode="legacy14"):
        self.python = Path(
            runtime_python
            or os.environ.get("PV3D_MULTIVIEW_PYTHON", ROOT / "services/multiview/.venv/bin/python")
        )
        self.script = Path(worker_script or ROOT / "services/multiview/infer.py")
        self.cache_dir = Path(cache_dir or os.environ.get("PV3D_MODEL_DIR", ROOT / "models/huggingface"))
        self.device = device or os.environ.get("PV3D_MULTIVIEW_DEVICE", os.environ.get("PV3D_DEVICE", "auto"))
        self.input_size = int(input_size or os.environ.get("PV3D_VGGT_SIZE", "336"))
        self.resize_mode = resize_mode
        if resize_mode not in {"legacy14", "isotropic"}:
            raise ValueError("Unsupported resize mode")
        if self.device not in {"auto", "cpu", "mps", "cuda"} or self.input_size not in {224, 336, 518}:
            raise ValueError("Unsupported multi-view inference settings")

    def status(self):
        return {
            "state": "available" if self.python.is_file() else "not_installed",
            "model_id": VGGT_ID,
            "revision": VGGT_REVISION,
            "device": self.device,
            "input_size": self.input_size,
        }

    def reconstruct(self, image_paths, output_dir, on_progress):
        if not self.python.is_file():
            raise RuntimeError("Run make setup-multiview to install the local model worker.")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = output_dir / "input.json"
        manifest.write_text(
            json.dumps(
                {
                    "images": [str(p) for p in image_paths],
                    "input_size": self.input_size,
                    "resize_mode": self.resize_mode,
                    "device": self.device,
                    "cache_dir": str(self.cache_dir),
                }
            ),
            encoding="utf-8",
        )
        on_progress("loading_geometry_model")
        with (output_dir / "worker.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [str(self.python), str(self.script), "--input", str(manifest), "--output", str(output_dir)],
                stdout=subprocess.PIPE,
                stderr=log,
                text=True,
            )
            timed_out = threading.Event()

            def terminate():
                timed_out.set()
                process.kill()

            deadline = threading.Timer(1800, terminate)
            deadline.daemon = True
            deadline.start()
            try:
                for line in iter(lambda: process.stdout.readline(8192), ""):
                    log.write(line)
                    log.flush()
                    try:
                        message = json.loads(line)
                    except ValueError:
                        continue
                    if message.get("stage") in {
                        "loading_geometry_model",
                        "estimating_geometry",
                        "unprojecting",
                    }:
                        on_progress(message["stage"])
                code = process.wait()
            finally:
                deadline.cancel()
                process.stdout.close()
                if process.poll() is None:
                    process.kill()
                    process.wait()
        if code != 0 or timed_out.is_set():
            raise RuntimeError("Multi-view model worker failed. Check the local worker log.")
        load_geometry(output_dir / "geometry.npz", len(image_paths))
        return json.loads((output_dir / "geometry.json").read_text(encoding="utf-8"))
