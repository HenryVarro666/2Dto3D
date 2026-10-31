"""The model boundary is slow; these tests pin our normalization/filtering behavior."""

import math

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
