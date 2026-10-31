"""Automatic SAM evidence must survive all the way into V3 point assignment."""

import json
from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image
from pv3d.app import create_app
from pv3d.perception import GroundingDetector
from pv3d.pointcloud import _mask
from pv3d.store import Store
from test_api import DetectorDouble, picture, upload
from test_multiview_api import GeometryBoundary, capture, multi_terminal


def topology(height, width):
    mask = np.zeros((height, width), bool)
    mask[1:5, 1:5] = True
    mask[2:4, 2:4] = False
    mask[7:9, 7:9] = True
    return mask


def test_automatic_segmenter_exposes_full_mask_without_changing_v2_contours(tmp_path, monkeypatch):
    import sys

    class Tensor:
        def __init__(self, value): self.value = value
        def cpu(self): return self
        def numpy(self): return self.value

    class Inputs(dict):
        def to(self, _device): return self

    class Processor:
        def __call__(self, **_kwargs): return Inputs(original_sizes=Tensor(np.array([[10, 10]])))
        def post_process_masks(self, *_args): return [Tensor(topology(10, 10)[None, None])]

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(inference_mode=nullcontext))
    detector = GroundingDetector(tmp_path, device="cpu")
    detector._sam_processor = Processor()
    detector._sam = lambda **_: SimpleNamespace(pred_masks=Tensor(None))
    monkeypatch.setattr(detector, "_load_segmenter", lambda: None)
    binary = {}
    detections = [{"bbox": [0, 0, 1, 1]}]
    detector._segment(Image.new("RGB", (10, 10)), detections, masks_out=binary)
    assert np.array_equal(binary[0], topology(10, 10))
    assert "mask_polygon" in detections[0]  # Legacy single-view display contract remains.
    old = [{"bbox": [0, 0, 1, 1]}]
    detector._segment(Image.new("RGB", (10, 10)), old)
    json.dumps(old)  # No binary ndarray leaks into the V2 detection contract.


def test_automatic_capture_persists_mask_topology_letterbox_and_manual_inheritance(tmp_path):
    class SegmentedDetector(DetectorDouble):
        def detect(self, image, on_progress=None, scene_mode="single", retain_masks=False):
            prediction = super().detect(image, on_progress, scene_mode)
            if retain_masks:
                prediction["binary_masks"] = {0: topology(image.height, image.width)}
            return prediction

    detector = SegmentedDetector([{"category": "cabinet", "label": "Housing", "bbox": [0, 0, 1, 1],
                                    "score": 0.8, "source": "grounding_dino"}])
    with TestClient(create_app(tmp_path, detector, reconstructor=GeometryBoundary())) as client:
        group = capture(client, [upload(client, picture((10, 10))), upload(client, picture((11, 10)))])
        queued = client.post("/api/multiview/jobs", json={"capture_id": group["id"]}).json()
        job = multi_terminal(client, queued["id"])
        assert job["result"], job
        first = job["result"]["observations"][0]
        assert first.get("refinement_id"), "Automatic point assignment needs authoritative binary evidence"
        path = tmp_path / "refinements" / first["refinement_id"] / "binary-mask.png"
        with Image.open(path) as raster:
            assert np.array_equal(np.asarray(raster) > 0, topology(10, 10))
        store = Store(tmp_path)
        mapped = _mask(first, group["assets"][0], [1, 2, 9, 8], (10, 10), store)
        expected = np.zeros((10, 10), bool)
        expected[2:8, 1:9] = np.asarray(Image.fromarray(topology(10, 10)).resize((8, 6), Image.Resampling.NEAREST))
        assert np.array_equal(mapped, expected)
        inputs = [{k: o[k] for k in ("id", "asset_id", "component_id", "category", "label", "bbox")}
                  for o in job["result"]["observations"]]
        submitted = client.post("/api/multiview/jobs", json={"capture_id": group["id"], "mode": "manual",
                                                            "base_job_id": job["id"], "observations": inputs})
        edited = multi_terminal(client, submitted.json()["id"])["result"]
        assert edited["observations"][0]["refinement_id"] == first["refinement_id"]
        assert edited["observations"][0]["source"] == "grounding_dino"
