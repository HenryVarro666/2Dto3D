"""The model boundary is slow; these tests pin our normalization/filtering behavior."""

import math

import pytest
from pv3d.perception import normalize_predictions


def test_predictions_clip_to_normalized_oriented_image_and_keep_real_categories():
    result = normalize_predictions(
        [[10, 20, 110, 80], [0, 0, 25, 20], [20, 70, 50, 100]],
        [0.72, 0.9, 0.55],
        ["electrical cabinet", "solar panel", "bundle of cables"],
        (100, 100),
    )
    assert [item["category"] for item in result] == ["cabinet", "cables"]
    assert result[0]["bbox"] == [0.1, 0.2, 1.0, 0.8]
    assert result[0]["source"] == "grounding_dino"
    assert result[0]["score"] == 0.72


def test_same_component_duplicate_is_suppressed_without_merging_distinct_support():
    result = normalize_predictions(
        [[10, 10, 80, 70], [11, 11, 79, 69], [45, 0, 55, 100]],
        [0.6, 0.8, 0.7],
        ["cabinet", "electrical box", "concrete pole"],
        (100, 100),
    )
    assert [item["category"] for item in result] == ["cabinet", "pole"]
    assert result[0]["bbox"] == [0.11, 0.11, 0.79, 0.69]


def test_invalid_model_boxes_and_scores_do_not_become_geometry():
    assert (
        normalize_predictions(
            [[10, 10, 10, 20], [0, 0, math.nan, 20], [0, 0, 40, 40], [150, 0, 200, 20]],
            [0.8, 0.8, math.inf, 0.7],
            ["cabinet"] * 4,
            (100, 100),
        )
        == []
    )


def test_blank_recognition_returns_no_invented_parts():
    assert normalize_predictions([], [], [], (800, 450)) == []


def test_single_target_does_not_turn_background_or_subpanels_into_extra_cabinets():
    result = normalize_predictions(
        [[20, 20, 65, 70], [22, 25, 32, 40], [80, 40, 98, 55], [33, 65, 48, 90]],
        [0.8, 0.6, 0.55, 0.5],
        ["inverter", "electrical cabinet", "cabinet", "bundle of cables"],
        (100, 100),
    )
    assert [d["category"] for d in result] == ["cabinet", "cables"]
    assert result[0]["bbox"] == [0.2, 0.2, 0.65, 0.7]


def test_multiple_scope_keeps_distinct_cabinets_and_distant_support_after_nms():
    result = normalize_predictions(
        [[20, 10, 60, 40], [22, 11, 59, 39], [20, 55, 65, 98], [80, 0, 90, 100]],
        [0.8, 0.7, 0.65, 0.6],
        ["inverter", "electrical cabinet", "electrical cabinet", "pole"],
        (100, 100),
        scene_mode="multiple",
    )
    assert [item["category"] for item in result] == ["cabinet", "cabinet", "pole"]
    assert result[1]["bbox"] == [0.2, 0.55, 0.65, 0.98]


def test_detector_health_recovers_after_transient_failure_without_reloading_weights(tmp_path):
    """Use the real Torch context; replace only the expensive loaded model boundary."""
    from types import SimpleNamespace

    from PIL import Image
    from pv3d.perception import GroundingDetector

    torch = pytest.importorskip("torch", reason="Optional ML dependency; this test downloads no weights")

    class Inputs(dict):
        def to(self, device):
            return self

    class Processor:
        def __call__(self, **kwargs):
            return Inputs(input_ids=torch.tensor([1]))

        def post_process_grounded_object_detection(self, *args, **kwargs):
            return [{"text_labels": [], "boxes": torch.empty(0, 4), "scores": torch.empty(0)}]

    class FlakyModel:
        config = SimpleNamespace(_commit_hash="test")

        def __init__(self):
            self.calls = 0

        def __call__(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("transient inference failure")

    detector = GroundingDetector(tmp_path, device="cpu")
    detector._model = FlakyModel()
    detector._processor = Processor()
    image = Image.new("RGB", (20, 20))
    with pytest.raises(RuntimeError, match="transient"):
        detector.detect(image)
    assert detector.status()["state"] == "error"
    assert detector.status()["error"] is not None
    assert detector.detect(image)["detections"] == []
    assert detector.status()["state"] == "ready"
    assert detector.status()["error"] is None
