"""Isolated real VGGT inference. Only normalized local images enter this process."""

import argparse
import gc
import hashlib
import json
import sys
import time
from contextlib import nullcontext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api/src"))
from pv3d.reconstruction import (
    ROOT,
    VGGT_CODE_REVISION,
    VGGT_ID,
    VGGT_REVISION,
    prepare_images,
)


def report(stage):
    print(json.dumps({"stage": stage}), flush=True)


def checkpoint(cache_dir):
    from huggingface_hub import hf_hub_download

    return hf_hub_download(
        VGGT_ID, "model.safetensors", revision=VGGT_REVISION, cache_dir=cache_dir, token=False
    )


def infer(manifest, output):
    import numpy as np
    import torch
    from safetensors import safe_open
    from vggt.models.vggt import VGGT
    from vggt.utils.geometry import unproject_depth_map_to_point_map
    from vggt.utils.pose_enc import pose_encoding_to_extri_intri

    started = time.perf_counter()
    torch.set_num_threads(4)
    device = manifest["device"]
    if device == "auto":
        device = (
            "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        )
    report("loading_geometry_model")
    weights = checkpoint(manifest["cache_dir"])
    model = VGGT(enable_point=False, enable_track=False)
    with safe_open(weights, framework="pt", device="cpu") as archive:
        state = {
            key: archive.get_tensor(key)
            for key in archive.keys()  # noqa: SIM118 - safe_open provides keys(), not dict iteration.
            if not key.startswith(("point_head.", "track_head."))
        }
    model.load_state_dict(state, strict=True)
    del state
    gc.collect()
    model = model.to(device).eval()
    loaded = time.perf_counter()
    resize_mode = manifest.get("resize_mode", "legacy14")
    images, rects = prepare_images(manifest["images"], manifest["input_size"], resize_mode=resize_mode)
    input_tensor_sha256 = hashlib.sha256(images.tobytes()).hexdigest()
    inputs = torch.from_numpy(images).to(device)
    report("estimating_geometry")
    precision = (
        torch.autocast(
            "cuda", dtype=torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
        )
        if device == "cuda"
        else nullcontext()
    )
    with torch.inference_mode(), precision:
        predictions = model(inputs)
    depth = predictions["depth"][0].float().cpu().numpy()
    confidence = predictions["depth_conf"][0].float().cpu().numpy()
    pose = predictions["pose_enc"].float().cpu()
    predicted = time.perf_counter()
    report("unprojecting")
    extrinsic, intrinsic = pose_encoding_to_extri_intri(pose, images.shape[-2:])
    extrinsic, intrinsic = extrinsic[0].numpy(), intrinsic[0].numpy()
    points = unproject_depth_map_to_point_map(depth, extrinsic, intrinsic)
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output / "geometry.npz",
        points=points.astype(np.float32),
        depth=depth[..., 0],
        confidence=confidence,
        colors=np.rint(images.transpose(0, 2, 3, 1) * 255).astype(np.uint8),
        rects=rects,
        extrinsics=extrinsic,
        intrinsics=intrinsic,
    )
    meta = {
        "input_tensor_sha256": input_tensor_sha256,
        "model": {
            "model_id": VGGT_ID,
            "revision": VGGT_REVISION,
            "code_revision": VGGT_CODE_REVISION,
            "device": device,
            "input_size": manifest["input_size"],
            "resize_mode": resize_mode,
            "license": "CC-BY-NC-4.0",
            "geometry": "joint_depth_and_camera_unprojection",
            "metric_scale_status": "unknown",
        },
        "timings": {
            "geometry_load_ms": (loaded - started) * 1000,
            "geometry_inference_ms": (predicted - loaded) * 1000,
            "geometry_unproject_ms": (time.perf_counter() - predicted) * 1000,
        },
    }
    (output / "geometry.json").write_text(json.dumps(meta, allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "models/huggingface")
    args = parser.parse_args()
    if args.prepare:
        checkpoint(args.cache_dir)
        print("Pinned VGGT checkpoint cached locally.")
    elif args.input and args.output:
        infer(json.loads(args.input.read_text(encoding="utf-8")), args.output)
    else:
        parser.error("Use --prepare, or --input and --output")
