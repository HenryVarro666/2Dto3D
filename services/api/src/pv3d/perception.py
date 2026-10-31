"""Real local recognition; model weights and image evidence stay on the host."""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import threading
import time
from pathlib import Path

MODEL_ID = "IDEA-Research/grounding-dino-tiny"
MODEL_REVISION = "a2bb814dd30d776dcf7e30523b00659f4f141c71"
SEGMENTATION_ID = "facebook/sam2.1-hiera-tiny"
SEGMENTATION_REVISION = "de431c4043854a71d8101e17995dfe596bf101a5"
PROMPT = (
    "a solar inverter. an electrical cabinet. a metal mounting bracket. a concrete pole. a bundle of cables."
)
LABELS = {"cabinet": "主机外壳", "bracket": "安装支架", "pole": "支撑立柱", "cables": "线缆束"}
log = logging.getLogger(__name__)


def _category(phrase: str) -> str | None:
    phrase = phrase.lower()
    if any(word in phrase for word in ("cabinet", "inverter", "electrical box")):
        return "cabinet"
    if any(word in phrase for word in ("bracket", "mounting")):
        return "bracket"
    if any(word in phrase for word in ("pole", "post", "column")):
        return "pole"
    if any(word in phrase for word in ("cable", "wire")):
        return "cables"
    return None


def _iou(a: list[float], b: list[float]) -> float:
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / max(area_a + area_b - intersection, 1e-12)


def normalize_predictions(boxes, scores, phrases, image_size) -> list[dict]:
    """Keep finite, supported predictions and remove duplicate same-class boxes."""
    width, height = image_size
    candidates = []
    for raw_box, raw_score, phrase in zip(boxes, scores, phrases):
        category = _category(str(phrase))
        score = float(raw_score)
        box = [float(value) for value in raw_box]
        if category is None or len(box) != 4 or not all(math.isfinite(v) for v in [*box, score]):
            continue
        if not 0 <= score <= 1 or width <= 0 or height <= 0:
            continue
        x1, y1, x2, y2 = [
            max(0.0, min(1.0, value / size)) for value, size in zip(box, [width, height, width, height])
        ]
        if x2 - x1 < 0.002 or y2 - y1 < 0.002:
            continue
        candidates.append(
            {
                "category": category,
                "label": LABELS[category],
                "bbox": [x1, y1, x2, y2],
                "score": round(score, 5),
                "source": "grounding_dino",
            }
        )
    kept = []
    for candidate in sorted(candidates, key=lambda item: -item["score"]):
        if any(
            candidate["category"] == prev["category"] and _iou(candidate["bbox"], prev["bbox"]) > 0.55
            for prev in kept
        ):
            continue
        kept.append(candidate)
    cabinets = [item for item in kept if item["category"] == "cabinet"]
    if cabinets:
        # The first release handles one selected equipment, not a whole station.
        primary = max(
            cabinets,
            key=lambda item: (
                item["score"]
                * math.sqrt((item["bbox"][2] - item["bbox"][0]) * (item["bbox"][3] - item["bbox"][1]))
            ),
        )
        x1, y1, x2, y2 = primary["bbox"]
        width, height = x2 - x1, y2 - y1
        kept = [
            item
            for item in kept
            if item is primary
            or (
                item["category"] != "cabinet"
                and x1 - width * 0.5 <= (item["bbox"][0] + item["bbox"][2]) / 2 <= x2 + width * 0.5
                and y1 - height <= (item["bbox"][1] + item["bbox"][3]) / 2 <= y2 + height
            )
        ]
    return kept[:12]


class GroundingDetector:
    def __init__(self, cache_dir: Path, device: str = "auto"):
        if device not in {"auto", "cpu", "mps", "cuda"}:
            raise ValueError("Unsupported inference device")
        self.cache_dir = Path(cache_dir)
        self.requested_device = device
        self.device = device
        self._state = "not_loaded"
        self._error = None
        self._model = None
        self._processor = None
        self._sam = None
        self._sam_processor = None
        self._segmentation_state = "not_loaded"
        self._lock = threading.Lock()

    def status(self) -> dict:
        return {
            "state": self._state,
            "model_id": MODEL_ID,
            "device": self.device,
            "error": self._error,
            "segmentation": self._segmentation_state,
        }

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self._state = "loading"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        torch.set_num_threads(int(os.environ.get("PV3D_TORCH_THREADS", "4")))
        if self.requested_device == "auto":
            self.device = (
                "cuda"
                if torch.cuda.is_available()
                else ("mps" if torch.backends.mps.is_available() else "cpu")
            )
        self._processor = AutoProcessor.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, cache_dir=self.cache_dir
        )
        self._model = (
            AutoModelForZeroShotObjectDetection.from_pretrained(
                MODEL_ID,
                revision=MODEL_REVISION,
                cache_dir=self.cache_dir,
                use_safetensors=True,
                disable_custom_kernels=True,
            )
            .to(self.device)
            .eval()
        )
        self._state = "ready"
        self._error = None

    def _load_segmenter(self) -> None:
        from transformers import Sam2Model, Sam2Processor

        if self._sam is None:
            self._segmentation_state = "loading"
            self._sam_processor = Sam2Processor.from_pretrained(
                SEGMENTATION_ID, revision=SEGMENTATION_REVISION, cache_dir=self.cache_dir
            )
            self._sam = (
                Sam2Model.from_pretrained(
                    SEGMENTATION_ID,
                    revision=SEGMENTATION_REVISION,
                    cache_dir=self.cache_dir,
                    use_safetensors=True,
                )
                .to(self.device)
                .eval()
            )
        self._sam.to(self.device)
        self._segmentation_state = "ready"

    def prepare(self) -> dict:
        """Cache both enabled checkpoints; a separate server still has its own cold load."""
        with self._lock:
            self._load()
            if os.environ.get("PV3D_SEGMENT", "1") == "1":
                self._load_segmenter()
            return self.status()

    def _segment(self, image, detections) -> None:
        import cv2
        import numpy as np
        import torch

        self._load_segmenter()
        boxes = [
            [v * side for v, side in zip(d["bbox"], [image.width, image.height, image.width, image.height])]
            for d in detections
        ]
        inputs = self._sam_processor(images=image, input_boxes=[boxes], return_tensors="pt").to(self.device)
        with torch.inference_mode():
            output = self._sam(**inputs, multimask_output=False)
        masks = self._sam_processor.post_process_masks(
            output.pred_masks.cpu(), inputs["original_sizes"].cpu()
        )[0]
        masks = masks.numpy().reshape(-1, image.height, image.width)
        for detection, mask in zip(detections, masks):
            contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(contour) < 9:
                continue
            contour = cv2.approxPolyDP(contour, 0.003 * cv2.arcLength(contour, True), True).reshape(-1, 2)
            if len(contour) < 3:
                continue
            if len(contour) > 128:
                contour = contour[:: max(1, math.ceil(len(contour) / 128))]
            detection["mask_polygon"] = [
                [round(float(x) / image.width, 6), round(float(y) / image.height, 6)] for x, y in contour
            ]
        self._segmentation_state = "ready"

    def detect(self, image) -> dict:
        import torch

        with self._lock:
            started = time.perf_counter()
            cold = self._model is None
            warnings = []
            try:
                self._load()
                loaded = time.perf_counter()
                inputs = self._processor(images=image, text=PROMPT, return_tensors="pt").to(self.device)
                try:
                    with torch.inference_mode():
                        output = self._model(**inputs)
                except (RuntimeError, NotImplementedError):
                    if self.requested_device != "auto" or self.device != "mps":
                        raise
                    self.device = "cpu"
                    self._model.to("cpu")
                    inputs = {key: value.to("cpu") for key, value in inputs.items()}
                    with torch.inference_mode():
                        output = self._model(**inputs)
                    warnings.append("MPS_FALLBACK_CPU")
                result = self._processor.post_process_grounded_object_detection(
                    output,
                    inputs["input_ids"],
                    threshold=0.24,
                    text_threshold=0.22,
                    target_sizes=[(image.height, image.width)],
                )[0]
                phrases = result["text_labels"] if "text_labels" in result else result["labels"]
                detections = normalize_predictions(
                    result["boxes"].cpu().tolist(), result["scores"].cpu().tolist(), phrases, image.size
                )
                detected = time.perf_counter()
                if detections and os.environ.get("PV3D_SEGMENT", "1") == "1":
                    try:
                        self._segment(image, detections)
                    except Exception:
                        # A segmentation failure must not turn genuine detector boxes into fake masks.
                        log.exception("Optional SAM2 segmentation unavailable; retaining detector boxes")
                        self._segmentation_state = "unavailable"
                        warnings.append("SAM2_UNAVAILABLE_BBOX_ONLY")
                else:
                    self._segmentation_state = "disabled"
                finished = time.perf_counter()
                self._state = "ready"
                self._error = None
                return {
                    "detections": detections,
                    "warnings": warnings,
                    "model": {
                        "model_id": MODEL_ID,
                        "revision": self._model.config._commit_hash,
                        "device": self.device,
                        "cold_start": cold,
                        "prompt": PROMPT,
                        "score_kind": "uncalibrated_model_score",
                        "segmentation_id": SEGMENTATION_ID if self._segmentation_state == "ready" else None,
                        "segmentation_revision": getattr(self._sam.config, "_commit_hash", None)
                        if self._sam
                        else None,
                        "segmentation_state": self._segmentation_state,
                    },
                    "timings": {
                        "load_ms": round((loaded - started) * 1000, 2),
                        "detection_ms": round((detected - loaded) * 1000, 2),
                        "segmentation_ms": round((finished - detected) * 1000, 2),
                    },
                }
            except Exception:
                self._state = "error"
                self._error = "模型加载或推理失败，请检查模型依赖、权重网络和设备配置。"
                raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or run the real local recognition adapter")
    parser.add_argument("image", nargs="?", type=Path)
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    parser.add_argument(
        "--cache-dir", type=Path, default=Path(__file__).resolve().parents[4] / "models" / "huggingface"
    )
    args = parser.parse_args()
    detector = GroundingDetector(args.cache_dir, args.device)
    if args.image:
        from PIL import Image, ImageOps

        with Image.open(args.image) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
        image.thumbnail((2048, 2048))
        print(json.dumps(detector.detect(image), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(detector.prepare(), ensure_ascii=False))


if __name__ == "__main__":
    main()
