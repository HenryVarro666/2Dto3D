"""Real local recognition; model weights and image evidence stay on the host."""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any

MODEL_ID = "IDEA-Research/grounding-dino-tiny"
MODEL_REVISION = "a2bb814dd30d776dcf7e30523b00659f4f141c71"
SEGMENTATION_ID = "facebook/sam2.1-hiera-tiny"
SEGMENTATION_REVISION = "de431c4043854a71d8101e17995dfe596bf101a5"
SAM_PRESETS = {
    "tiny": (SEGMENTATION_ID, SEGMENTATION_REVISION),
    "small": ("facebook/sam2.1-hiera-small", "ee5bba1d82bb8749febdf90f45e84b687142ba03"),
    "base-plus": ("facebook/sam2.1-hiera-base-plus", "b7320756a13354e7530a63935656d35b2f91a290"),
    "large": ("facebook/sam2.1-hiera-large", "665f8e2ad61cf5f53d65644ff27c8ee525124610"),
}
PROMPT = (
    "a solar inverter. an electrical cabinet. a metal mounting bracket. a concrete pole. a bundle of cables."
    " an electrical connector. a cable tray."
)
LABELS = {"cabinet": "主机外壳", "bracket": "安装支架", "pole": "支撑立柱", "cables": "线缆束",
          "connector": "接线插接件", "cable_tray": "电缆线槽"}
CLASS_WORDS = {
    "inverter": ("inverter",),
    "cabinet": ("cabinet",),
    "bracket": ("bracket",),
    "pole": ("pole",),
    "cables": ("bundle", "cables"),
    "connector": ("connector",),
    "cable_tray": ("tray",),
}
FILTER_POLICY = "prompt_roles_and_component_context_v3"
log = logging.getLogger(__name__)


def prompt_class_scores(probabilities, offsets) -> list[dict[str, float]]:
    """Use prompt noun spans, not decoded fragments or high-scoring determiners.

    All wordpieces of a noun must support it. A lone '##verter' must not turn a
    person into an inverter. 'bundle' can recover the cable query, but remains
    subject to equipment-context filtering.
    """
    word_indices = {}
    for words in CLASS_WORDS.values():
        for word in words:
            start = PROMPT.index(word)
            stop = start + len(word)
            word_indices[word] = [i for i, (a, b) in enumerate(offsets) if b > a >= start and b <= stop]
    return [
        {
            kind: max(
                (min(float(query[i]) for i in word_indices[word]) if word_indices[word] else 0.0)
                for word in words
            )
            for kind, words in CLASS_WORDS.items()
        }
        for query in probabilities
    ]


def _category(phrase: str) -> str | None:
    phrase = phrase.lower()
    if "connector" in phrase:
        return "connector"
    if "tray" in phrase:
        return "cable_tray"
    if any(word in phrase for word in ("cabinet", "inverter", "electrical box")):
        return "cabinet"
    if any(word in phrase for word in ("bracket", "mounting")):
        return "bracket"
    if any(word in phrase for word in ("pole", "post", "column")):
        return "pole"
    if any(word in phrase for word in ("cable", "wire", "bundle")):
        return "cables"
    return None


def _iou(a: list[float], b: list[float]) -> float:
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / max(area_a + area_b - intersection, 1e-12)


def normalize_predictions(
    boxes, scores, phrases, image_size, scene_mode="single", *, class_scores=None, diagnostics=None
) -> list[dict]:
    """Keep finite, supported predictions and remove duplicate same-class boxes."""
    width, height = image_size
    candidates = []
    if class_scores is not None and len(class_scores) != len(boxes):
        raise ValueError("Prompt class evidence must align with detector boxes")
    for index, (raw_box, raw_score, phrase) in enumerate(zip(boxes, scores, phrases)):
        phrase = str(phrase).lower()
        evidence = class_scores[index] if class_scores is not None else None
        if evidence is not None:
            kind = max(evidence, key=evidence.get, default=None)
            category = ("cabinet" if kind == "inverter" else kind) if kind else None
            if kind is not None and evidence[kind] <= 0.22:
                category = None
            specific_inverter = evidence.get("inverter", 0) > 0.22
        else:
            category = _category(phrase)
            specific_inverter = "inverter" in phrase
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
                "_inverter": specific_inverter,
                "_ambiguous_bundle": category == "cables"
                and "bundle" in phrase
                and not any(word in phrase for word in ("cable", "wire")),
            }
        )
    def area(item):
        x1, y1, x2, y2 = item["bbox"]
        return (x2 - x1) * (y2 - y1)

    specific = [
        item for item in candidates if item["category"] == "cabinet" and item["_inverter"] and area(item) >= 0.01
    ]
    mapped_count = len(candidates)
    context_rejected = 0
    bounded = []
    for item in candidates:
        envelope = False
        if item["category"] == "cabinet" and not item["_inverter"]:
            envelope = area(item) > 0.65
            for device in specific:
                a, b = item["bbox"], device["bbox"]
                overlap = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
                    0, min(a[3], b[3]) - max(a[1], b[1])
                )
                if overlap >= 0.9 * area(device) and area(item) > 1.8 * area(device):
                    envelope = True
        if envelope:
            context_rejected += 1
        else:
            bounded.append(item)
    equipment = [item for item in bounded if item["category"] == "cabinet" and area(item) >= 0.01]

    def connector_context(item):
        cx, cy = (item["bbox"][0] + item["bbox"][2]) / 2, (item["bbox"][1] + item["bbox"][3]) / 2
        for device in equipment:
            x1, y1, x2, y2 = device["bbox"]
            w, h = x2 - x1, y2 - y1
            if (x1 - w * 0.2 <= cx <= x2 + w * 0.2 and y1 - h * 0.1 <= cy <= y2 + h * 0.6
                    and area(item) <= area(device) * 0.25):
                return True
        return False

    before_context = len(bounded)
    bounded = [item for item in bounded if item["category"] != "connector" or connector_context(item)]
    connectors: list[dict] = []
    for item in sorted((item for item in bounded if item["category"] == "connector"),
                       key=lambda item: -item["score"]):
        if not any(_iou(item["bbox"], previous["bbox"]) > 0.55 for previous in connectors):
            connectors.append(item)
    valid = []
    for item in bounded:
        if item["category"] == "cable_tray":
            x1, y1, x2, y2 = item["bbox"]
            w, h = (x2 - x1) * width, (y2 - y1) * height
            if max(w, h) < 2 * min(w, h):
                continue  # A square neighboring enclosure is not a tray.
            contained = 0
            for plug in connectors:
                a, b, c, d = plug["bbox"]
                overlap = max(0, min(x2, c) - max(x1, a)) * max(0, min(y2, d) - max(y1, b))
                contained += overlap >= 0.8 * area(plug)
            if contained >= 2:
                continue  # An envelope around a row of plugs is not a second tray.
        valid.append(item)
    context_rejected_parts = before_context - len(valid)
    # Explicit electrical/linear roles supersede overlapping generic bracket/cabinet queries.
    overrides = {"bracket": "connector", "cabinet": "cable_tray"}
    bounded = [item for item in valid if not (item["category"] in overrides and not item["_inverter"]
               and any(part["category"] == overrides[item["category"]] and _iou(item["bbox"], part["bbox"]) > 0.55
                       for part in valid))]
    kept: list[dict] = []
    # Reject envelopes before NMS. An unusable small fragment must not suppress
    # a viable overlapping body, even when only the fragment says "inverter".
    for candidate in sorted(
        bounded,
        key=lambda item: (
            item["category"] == "cabinet" and area(item) >= 0.01,
            item["category"] == "cabinet" and item["_inverter"],
            item["score"],
        ),
        reverse=True,
    ):
        if any(
            candidate["category"] == prev["category"] and _iou(candidate["bbox"], prev["bbox"]) > 0.55
            for prev in kept
        ):
            continue
        kept.append(candidate)
    kept.sort(key=lambda item: -item["score"])
    post_nms_count = len(kept)
    # Tiny corner boxes cannot establish a whole equipment or its relative scale.
    anchors = [item for item in kept if item["category"] == "cabinet" and area(item) >= 0.01]
    if not anchors:
        kept = [item for item in kept if item["category"] != "cabinet"]

    def near_equipment(item, device):
        x1, y1, x2, y2 = device["bbox"]
        width, height = x2 - x1, y2 - y1
        cx, cy = (item["bbox"][0] + item["bbox"][2]) / 2, (item["bbox"][1] + item["bbox"][3]) / 2
        return x1 - width * 0.5 <= cx <= x2 + width * 0.5 and y1 - height <= cy <= y2 + height

    ambiguous_rejected = sum(
        item["_ambiguous_bundle"] and not any(near_equipment(item, device) for device in anchors)
        for item in kept
    )
    kept = [
        item
        for item in kept
        if not item["_ambiguous_bundle"] or any(near_equipment(item, device) for device in anchors)
    ]
    cabinets = [item for item in kept if item["category"] == "cabinet"]
    primary = None
    if cabinets and scene_mode == "single":
        # The first release handles one selected equipment, not a whole station.
        primary = max(
            anchors,
            key=lambda item: (item["_inverter"], item["score"]),
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
    if diagnostics is not None:
        diagnostics.update(
            policy=FILTER_POLICY,
            input_candidates=len(boxes),
            mapped_candidates=mapped_count,
            post_nms_count=post_nms_count,
            guards={
                "min_equipment_anchor_area": 0.01,
                "max_generic_cabinet_area": 0.65,
                "context_envelope_containment": 0.9,
                "context_envelope_area_ratio": 1.8,
            },
            rejected_context_cabinets=context_rejected,
            rejected_component_context=context_rejected_parts,
            rejected_overlapping_generic_roles=len(valid) - len(bounded),
            primary_anchor_established=bool(anchors),
            rejected_unanchored_bundles=ambiguous_rejected,
            primary_bbox=primary["bbox"] if primary else None,
            primary_kind=("inverter" if primary["_inverter"] else "cabinet") if primary else None,
            retained=len(kept[:12]),
        )
    return [{key: value for key, value in item.items() if not key.startswith("_")} for item in kept[:12]]


class GroundingDetector:
    def __init__(self, cache_dir: Path, device: str = "auto", sam_size: str | None = None):
        if device not in {"auto", "cpu", "mps", "cuda"}:
            raise ValueError("Unsupported inference device")
        self.cache_dir = Path(cache_dir)
        self.requested_device = device
        self.device = device
        self.sam_size = sam_size or os.environ.get("PV3D_SAM_SIZE", "tiny")
        if self.sam_size not in SAM_PRESETS:
            raise ValueError("Unsupported SAM size")
        self.sam_model_id, self.sam_revision = SAM_PRESETS[self.sam_size]
        self._state = "not_loaded"
        self._error: str | None = None
        self._model: Any = None
        self._processor: Any = None
        self._sam: Any = None
        self._sam_processor: Any = None
        self._segmentation_state = "not_loaded"
        self._lock = threading.Lock()
        self._embedding_cache: OrderedDict[tuple, Any] = OrderedDict()

    def status(self) -> dict:
        return {
            "state": self._state,
            "model_id": MODEL_ID,
            "device": self.device,
            "error": self._error,
            "segmentation": self._segmentation_state,
            "segmentation_model_id": self.sam_model_id,
        }

    def _resolve_device(self):
        import torch

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        torch.set_num_threads(int(os.environ.get("PV3D_TORCH_THREADS", "4")))
        if self.device == "auto":
            self.device = (
                "cuda"
                if torch.cuda.is_available()
                else ("mps" if torch.backends.mps.is_available() else "cpu")
            )

    def _load(self) -> None:
        if self._model is not None:
            return
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self._state = "loading"
        self._resolve_device()
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

        self._resolve_device()
        if self._sam is None:
            self._segmentation_state = "loading"
            self._sam_processor = Sam2Processor.from_pretrained(
                self.sam_model_id, revision=self.sam_revision, cache_dir=self.cache_dir
            )
            self._sam = (
                Sam2Model.from_pretrained(
                    self.sam_model_id,
                    revision=self.sam_revision,
                    cache_dir=self.cache_dir,
                    use_safetensors=True,
                )
                .to(self.device)
                .eval()
            )
        self._sam.to(self.device)
        self._segmentation_state = "ready"

    def refine(self, image, bbox, points, cache_key) -> dict:
        """Use box+point prompts, caching only two image feature sets under the shared model lock."""
        import torch

        with self._lock:
            started = time.perf_counter()
            self._load_segmenter()
            loaded = time.perf_counter()
            prompt = {
                "input_boxes": [
                    [
                        [
                            bbox[0] * image.width,
                            bbox[1] * image.height,
                            bbox[2] * image.width,
                            bbox[3] * image.height,
                        ]
                    ]
                ]
            }
            if points:
                prompt.update(
                    input_points=[[[[p["x"] * image.width, p["y"] * image.height] for p in points]]],
                    input_labels=[[[p["label"] for p in points]]],
                )
            inputs = self._sam_processor(images=image, return_tensors="pt", **prompt).to(self.device)
            key = (cache_key, self.sam_model_id, self.sam_revision, self.device, image.size)
            hit = key in self._embedding_cache
            with torch.inference_mode():
                if not hit:
                    self._embedding_cache[key] = self._sam.get_image_embeddings(inputs["pixel_values"])
                    while len(self._embedding_cache) > 2:
                        self._embedding_cache.popitem(last=False)
                self._embedding_cache.move_to_end(key)
                output = self._sam(
                    image_embeddings=self._embedding_cache[key],
                    multimask_output=False,
                    **{
                        k: v
                        for k, v in inputs.items()
                        if k in {"input_boxes", "input_points", "input_labels"}
                    },
                )
            masks = self._sam_processor.post_process_masks(
                output.pred_masks.cpu(), inputs["original_sizes"].cpu()
            )[0]
            self._segmentation_state = "ready"
            return {
                "mask": masks.numpy().reshape(-1, image.height, image.width)[0].astype(bool),
                "model": {
                    "model_id": self.sam_model_id,
                    "revision": self.sam_revision,
                    "device": self.device,
                    "prompt_kind": "box_and_points",
                    "embedding_cache_hit": hit,
                },
                "timings": {
                    "load_ms": round((loaded - started) * 1000, 2),
                    "refine_ms": round((time.perf_counter() - loaded) * 1000, 2),
                },
            }

    def prepare(self) -> dict:
        """Cache both enabled checkpoints; a separate server still has its own cold load."""
        with self._lock:
            self._load()
            if os.environ.get("PV3D_SEGMENT", "1") == "1":
                self._load_segmenter()
            return self.status()

    def _segment(self, image, detections, on_progress=None, masks_out=None) -> None:
        if on_progress:
            on_progress("loading_segmentation" if self._sam is None else "segmenting")
        import cv2
        import numpy as np
        import torch

        self._load_segmenter()
        if on_progress:
            on_progress("segmenting")
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
        for index, (detection, mask) in enumerate(zip(detections, masks)):
            if masks_out is not None and np.any(mask):
                # V3 retains the full raster before legacy contour simplification.
                masks_out[index] = mask.astype(bool).copy()
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

    def detect(self, image, on_progress: Callable[[str], None] | None = None,
               scene_mode="single", *, retain_masks=False) -> dict:
        with self._lock:
            started = time.perf_counter()
            cold = self._model is None
            warnings: list[str] = []
            binary_masks: dict[int, Any] = {}
            try:
                if on_progress:
                    on_progress("loading_model" if cold else "detecting")
                import torch

                self._load()
                loaded = time.perf_counter()
                if on_progress:
                    on_progress("detecting")
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
                class_scores = None
                if len(result["boxes"]):
                    tokenized = self._processor.tokenizer(PROMPT, return_offsets_mapping=True)
                    if tokenized["input_ids"] != inputs["input_ids"][0].cpu().tolist():
                        raise ValueError("Prompt token offsets differ from the model input")
                    probabilities = output.logits[0].sigmoid()
                    # Same query order/threshold as the installed processor's post-processing.
                    selected = probabilities[probabilities.max(dim=-1).values > 0.24]
                    class_scores = prompt_class_scores(selected.cpu().tolist(), tokenized["offset_mapping"])
                filter_diagnostics: dict[str, Any] = {}
                detections = normalize_predictions(
                    result["boxes"].cpu().tolist(),
                    result["scores"].cpu().tolist(),
                    phrases,
                    image.size,
                    scene_mode=scene_mode,
                    class_scores=class_scores,
                    diagnostics=filter_diagnostics,
                )
                detected = time.perf_counter()
                if detections and os.environ.get("PV3D_SEGMENT", "1") == "1":
                    try:
                        self._segment(image, detections, on_progress=on_progress,
                                      masks_out=binary_masks if retain_masks else None)
                    except Exception:
                        # A segmentation failure must not turn genuine detector boxes into fake masks.
                        log.exception("Optional SAM2 segmentation unavailable; retaining detector boxes")
                        self._segmentation_state = "unavailable"
                        binary_masks.clear()
                        warnings.append("SAM2_UNAVAILABLE_BBOX_ONLY")
                else:
                    self._segmentation_state = "disabled"
                finished = time.perf_counter()
                self._state = "ready"
                self._error = None
                return {
                    "detections": detections,
                    **({"binary_masks": binary_masks} if retain_masks else {}),
                    "warnings": warnings,
                    "model": {
                        "model_id": MODEL_ID,
                        "scene_mode": scene_mode,
                        "revision": self._model.config._commit_hash,
                        "device": self.device,
                        "cold_start": cold,
                        "prompt": PROMPT,
                        "score_kind": "uncalibrated_model_score",
                        "label_mapping": "complete_prompt_noun_wordpieces",
                        "filtering": filter_diagnostics,
                        "segmentation_id": self.sam_model_id if self._segmentation_state == "ready" else None,
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
