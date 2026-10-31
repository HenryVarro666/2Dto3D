"""Exercise the real HTTP/store/mask boundary; replace only the expensive SAM call."""

import io
import threading

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from test_api import DetectorDouble, factory, terminal, upload


class RefinerDouble(DetectorDouble):
    def __init__(self, *, empty=False, failure=None, release=None):
        super().__init__(release=release)
        self.empty = empty
        self.refine_failure = failure
        self.calls = []

    def refine(self, image, bbox, points, cache_key):
        self.calls.append((image.size, bbox, points, cache_key))
        if self.refine_failure:
            raise self.refine_failure
        mask = np.zeros((image.height, image.width), dtype=bool)
        if not self.empty:
            mask[20:80, 40:110] = True
            mask[40:60, 60:80] = False  # A genuine hole, not an extra component.
            mask[110:150, 150:190] = True  # A disconnected part of the same prompted object.
            mask[:5, :5] = True  # Must be clipped outside the user's box.
        return {
            "mask": mask,
            "model": {"model_id": "test-sam", "revision": "test"},
            "timings": {"refine_ms": 1},
        }


def request(client, asset_id, **overrides):
    return client.post(
        "/api/refinements", json={"asset_id": asset_id, "bbox": [0.1, 0.05, 0.8, 0.9], **overrides}
    )


def test_guided_mask_persists_disconnected_regions_holes_and_authoritative_geometry(tmp_path):
    detector = RefinerDouble()
    with TestClient(factory(tmp_path, detector)) as client:
        asset = upload(client)
        points = [{"x": 0.15, "y": 0.15, "label": 1}, {"x": 0.2, "y": 0.25, "label": 0}]
        response = request(client, asset["id"], points=points)
        assert response.status_code == 201, response.text
        ref = response.json()
        assert ref["points"] == points
        assert ref["geometry_bbox"] == [0.125, 0.1, 0.59375, 0.75]
        assert len(ref["mask_polygons"]) >= 3
        assert detector.calls[0][:3] == ((320, 200), (0.1, 0.05, 0.8, 0.9), points)
        preview = client.get(ref["mask_url"])
        assert preview.status_code == 200
        rgba = np.array(Image.open(io.BytesIO(preview.content)).convert("RGBA"))
        assert rgba[30, 45, 3] > 0
        assert rgba[50, 70, 3] == 0
        assert rgba[120, 165, 3] > 0
        assert rgba[2, 2, 3] == 0
        assert (tmp_path / "refinements" / ref["id"] / "binary-mask.png").is_file()
        response = client.post(
            "/api/jobs",
            json={
                "asset_id": asset["id"],
                "mode": "manual",
                "components": [
                    {
                        "id": "guided-cables",
                        "category": "cables",
                        "label": "User cables",
                        "bbox": ref["geometry_bbox"],
                        "refinement_id": ref["id"],
                    }
                ],
            },
        )
        assert response.status_code == 202, response.text
        job = terminal(client, response.json()["id"])
        component = job["result"]["components"][0]
        assert component["id"] == "guided-cables"
        assert component["source"] == "manual" and component["score"] is None
        assert component["refinement_id"] == ref["id"]
        assert component["mask_polygons"] == ref["mask_polygons"]
        assert component["mask_model"]["model_id"] == "test-sam"
        assert client.get(job["result"]["scene_url"]).status_code == 200
        manual = {key: component[key] for key in ("id", "category", "label", "bbox")}
        response = client.post(
            "/api/jobs",
            json={
                "asset_id": asset["id"],
                "mode": "manual",
                "base_job_id": job["id"],
                "components": [{**manual, "label": "Renamed cables"}],
            },
        )
        inherited = terminal(client, response.json()["id"])["result"]["components"][0]
        assert inherited["refinement_id"] == ref["id"] and inherited["mask_polygons"] == ref["mask_polygons"]
        response = client.post(
            "/api/jobs",
            json={
                "asset_id": asset["id"],
                "mode": "manual",
                "base_job_id": job["id"],
                "components": [{**manual, "refinement_id": None}],
            },
        )
        cleared = terminal(client, response.json()["id"])["result"]["components"][0]
        assert cleared["refinement_id"] is None and cleared["mask_polygons"] is None
        assert (
            client.get(ref["mask_url"]).content == preview.content
        )  # Clearing a version never mutates evidence.
    with TestClient(factory(tmp_path, RefinerDouble())) as restarted:
        assert restarted.get(ref["mask_url"]).content == preview.content
        assert (
            restarted.get(f"/api/jobs/{job['id']}/result").json()["components"][0]["refinement_id"]
            == ref["id"]
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"bbox": [0, 0, 0, 1]},
        {"bbox": [0, 0, 2, 1]},
        {"points": [{"x": 0.2, "y": 0.2, "label": 3}]},
        {"points": [{"x": 0.95, "y": 0.95, "label": 1}]},
        {"points": [{"x": -1, "y": 0.2, "label": 0}]},
        {"points": [{"x": 0.2, "y": 0.2, "label": 1}] * 65},
    ],
)
def test_invalid_prompts_are_rejected_before_any_model_call(tmp_path, overrides):
    detector = RefinerDouble()
    with TestClient(factory(tmp_path, detector)) as client:
        assert request(client, upload(client)["id"], **overrides).status_code == 422
        assert detector.calls == []


def test_refinement_references_cannot_cross_images_or_forge_a_different_bbox(tmp_path):
    with TestClient(factory(tmp_path, RefinerDouble())) as client:
        first, second = upload(client), upload(client)
        ref = request(client, first["id"]).json()
        component = {
            "id": "a",
            "category": "unknown",
            "label": "Box",
            "bbox": ref["geometry_bbox"],
            "refinement_id": ref["id"],
        }

        def manual(asset_id, comp):
            return client.post(
                "/api/jobs", json={"asset_id": asset_id, "mode": "manual", "components": [comp]}
            )

        assert manual(second["id"], component).status_code == 400
        assert manual(first["id"], {**component, "bbox": [0.1, 0.1, 0.9, 0.9]}).status_code == 400
        assert (
            manual(first["id"], {**component, "mask_polygons": [[[0, 0], [1, 0], [1, 1]]]}).status_code == 422
        )
        assert client.get("/api/refinements/" + "a" * 32 + "/mask.png").status_code == 404


@pytest.mark.parametrize(
    "detector, status",
    [(RefinerDouble(empty=True), 422), (RefinerDouble(failure=RuntimeError("private /host/path")), 503)],
)
def test_empty_or_failed_refinement_does_not_invent_an_artifact(tmp_path, detector, status):
    with TestClient(factory(tmp_path, detector)) as client:
        response = request(client, upload(client)["id"])
        assert response.status_code == status
        assert "private" not in response.text and "/host/path" not in response.text
        assert not list((tmp_path / "refinements").glob("*/mask.png"))


def test_refinement_shares_the_existing_bounded_inference_queue(tmp_path):
    gate = threading.Event()
    detector = RefinerDouble(release=gate)
    with TestClient(factory(tmp_path, detector)) as client:
        asset = upload(client)
        try:
            for _ in range(8):
                assert client.post("/api/jobs", json={"asset_id": asset["id"]}).status_code == 202
            assert request(client, asset["id"]).status_code == 409
            assert detector.calls == []
        finally:
            gate.set()


def test_refiner_reuses_image_embeddings_but_forwards_each_new_point_prompt(tmp_path):
    from types import SimpleNamespace

    from pv3d.perception import GroundingDetector

    torch = pytest.importorskip("torch", reason="Optional ML adapter test; downloads no weights")

    class Inputs(dict):
        def to(self, device):
            return self

    class Processor:
        def __call__(self, images, **kwargs):
            return Inputs(
                pixel_values=torch.zeros(1, 3, 24, 32),
                original_sizes=torch.tensor([[24, 32]]),
                **{key: torch.tensor(value) for key, value in kwargs.items() if key.startswith("input_")},
            )

        def post_process_masks(self, masks, sizes):
            return [masks[0]]

    class Sam:
        config = SimpleNamespace(_commit_hash="test-revision")

        def __init__(self):
            self.embedding_calls = 0
            self.prompts = []

        def to(self, device):
            return self

        def get_image_embeddings(self, pixel_values):
            self.embedding_calls += 1
            return [torch.ones(1, 1, 1)]

        def __call__(self, **kwargs):
            self.prompts.append(kwargs)
            return SimpleNamespace(pred_masks=torch.ones(1, 1, 1, 24, 32))

    detector = GroundingDetector(tmp_path, device="cpu")
    detector._sam, detector._sam_processor = Sam(), Processor()
    image = Image.new("RGB", (32, 24))
    first = detector.refine(image, (0.1, 0.1, 0.9, 0.9), [], "asset-a")
    second = detector.refine(image, (0.1, 0.1, 0.9, 0.9), [{"x": 0.5, "y": 0.25, "label": 1}], "asset-a")
    assert detector._sam.embedding_calls == 1
    assert first["model"]["embedding_cache_hit"] is False
    assert second["model"]["embedding_cache_hit"] is True
    assert second["mask"].shape == (24, 32)
    assert detector._model is None  # Refinement must not download or load DINO.
    np.testing.assert_allclose(detector._sam.prompts[-1]["input_points"].numpy(), [[[[16, 6]]]])
    assert detector._sam.prompts[-1]["input_labels"].tolist() == [[[1]]]
    for key in ("asset-b", "asset-c", "asset-a"):
        detector.refine(image, (0.1, 0.1, 0.9, 0.9), [], key)
    assert detector._sam.embedding_calls == 4  # Two-image LRU evicted asset-a.


def test_unknown_sam_model_size_is_rejected_before_loading_any_weights(tmp_path, monkeypatch):
    from pv3d.perception import GroundingDetector

    monkeypatch.setenv("PV3D_SAM_SIZE", "untrusted/path")
    with pytest.raises(ValueError, match="Unsupported SAM size"):
        GroundingDetector(tmp_path)
