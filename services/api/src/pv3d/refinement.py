"""Persist prompted masks without discarding disconnected regions or holes."""

import json
import math
from uuid import uuid4

import cv2
import numpy as np
from PIL import Image

from .schemas import Refinement


class EmptyRegionError(ValueError):
    pass


def save_refinement(data_dir, asset, request, prediction):
    width, height = asset["width"], asset["height"]
    mask = np.asarray(prediction["mask"], dtype=bool)
    if mask.shape != (height, width):
        raise ValueError("refiner returned incorrect mask shape")
    x1, y1, x2, y2 = request.bbox
    allowed = np.zeros_like(mask)
    allowed[
        math.floor(y1 * height) : math.ceil(y2 * height), math.floor(x1 * width) : math.ceil(x2 * width)
    ] = True
    mask = mask & allowed
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        raise EmptyRegionError("No usable region")
    bounds = [
        max(x1, xs.min() / width),
        max(y1, ys.min() / height),
        min(x2, (xs.max() + 1) / width),
        min(y2, (ys.max() + 1) / height),
    ]
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    rings = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:64]:
        contour = cv2.approxPolyDP(contour, 0.0015 * cv2.arcLength(contour, True), True).reshape(-1, 2)
        if len(contour) < 3:
            continue
        contour = contour[:: max(1, math.ceil(len(contour) / 128))]
        rings.append([[round(float(x) / width, 6), round(float(y) / height, 6)] for x, y in contour])
    warnings = []
    if any(
        bool(mask[min(height - 1, int(p.y * height)), min(width - 1, int(p.x * width))]) != bool(p.label)
        for p in request.points
    ):
        warnings.append("Some prompt points were not satisfied. Add points or redraw the box.")
    identifier = uuid4().hex
    result = Refinement(
        id=identifier,
        asset_id=asset["id"],
        bbox=request.bbox,
        geometry_bbox=[round(float(value), 6) for value in bounds],  # type: ignore[arg-type]
        points=request.points,
        mask_polygons=rings,  # type: ignore[arg-type]
        mask_url=f"/api/refinements/{identifier}/mask.png",
        model=prediction.get("model", {}),
        timings=prediction.get("timings", {}),
        warnings=warnings,
    ).model_dump(mode="json")
    folder = data_dir / "refinements" / identifier
    folder.mkdir(parents=True)
    Image.fromarray(mask.astype(np.uint8) * 255).save(folder / "binary-mask.png")
    overlay = np.zeros((height, width, 4), dtype=np.uint8)
    overlay[mask] = [24, 150, 114, 105]
    Image.fromarray(overlay).save(folder / "mask.png")
    (folder / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )
    return result
