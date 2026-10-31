"""Regression behavior from real partial-label, scene-envelope and target-choice failures."""

import pytest
from pv3d import perception


def test_partial_bundle_is_kept_near_a_real_inverter():
    result = perception.normalize_predictions(
        [[20, 10, 80, 50], [30, 48, 60, 90]],
        [0.7, 0.45],
        ["a solar inverter", "a bundle"],
        (100, 100),
        scene_mode="multiple",
    )
    assert [item["category"] for item in result] == ["cabinet", "cables"]
    assert result[1]["bbox"] == [0.3, 0.48, 0.6, 0.9]


def test_bundle_on_empty_supports_does_not_invent_wiring():
    result = perception.normalize_predictions(
        [[10, 10, 80, 70], [10, 30, 15, 95]],
        [0.44, 0.4],
        ["a bundle", "a concrete pole"],
        (100, 100),
        scene_mode="multiple",
    )
    assert [item["category"] for item in result] == ["pole"]


def test_scene_envelope_does_not_hide_two_distinct_inverters():
    result = perception.normalize_predictions(
        [[0, 0, 99, 99], [5, 20, 45, 70], [65, 30, 90, 65]],
        [0.8, 0.68, 0.31],
        ["an electrical cabinet", "a solar inverter", "a solar inverter"],
        (100, 100),
        scene_mode="multiple",
    )
    assert [item["bbox"] for item in result] == [
        [0.05, 0.2, 0.45, 0.7],
        [0.65, 0.3, 0.9, 0.65],
    ]


def test_large_closeup_with_specific_inverter_evidence_is_not_an_envelope():
    result = perception.normalize_predictions(
        [[2, 2, 98, 97]],
        [0.7],
        ["a solar inverter"],
        (100, 100),
        scene_mode="multiple",
    )
    assert len(result) == 1
    assert result[0]["bbox"] == [0.02, 0.02, 0.98, 0.97]


def test_single_prefers_inverter_over_larger_higher_scoring_adjacent_electrical_cabinet():
    result = perception.normalize_predictions(
        [[0, 30, 30, 95], [40, 10, 70, 40]],
        [0.85, 0.52],
        ["an electrical cabinet", "a solar inverter"],
        (100, 100),
    )
    assert len(result) == 1
    assert result[0]["bbox"] == [0.4, 0.1, 0.7, 0.4]


def test_tiny_corner_inverter_candidate_is_not_a_primary_scale_anchor():
    result = perception.normalize_predictions(
        [[97, 71, 99.9, 75], [70, 20, 74, 65]],
        [0.31, 0.29],
        ["a solar inverter", "a concrete pole"],
        (100, 100),
        scene_mode="multiple",
    )
    assert [item["category"] for item in result] == ["pole"]


def test_tiny_specific_fragment_does_not_outrank_a_usable_generic_device_body():
    result = perception.normalize_predictions(
        [[97, 71, 99.9, 75], [35, 25, 75, 80]],
        [0.4, 0.36],
        ["a solar inverter", "an electrical cabinet"],
        (100, 100),
    )
    assert [item["bbox"] for item in result] == [[0.35, 0.25, 0.75, 0.8]]


@pytest.mark.parametrize("scene_mode", ["single", "multiple"])
def test_anchor_ineligible_fragment_cannot_suppress_a_usable_overlapping_device(scene_mode):
    result = perception.normalize_predictions(
        [[41, 41, 50, 50], [40, 40, 51, 51]],
        [0.31, 0.72],
        ["a solar inverter", "an electrical cabinet"],
        (100, 100),
        scene_mode=scene_mode,
    )
    assert [item["bbox"] for item in result] == [[0.4, 0.4, 0.51, 0.51]]


@pytest.mark.parametrize("scene_mode", ["single", "multiple"])
def test_rejected_scene_envelope_cannot_suppress_a_usable_overlapping_cabinet(scene_mode):
    result = perception.normalize_predictions(
        [[5, 5, 95, 95], [10, 10, 90, 85]],
        [0.85, 0.72],
        ["an electrical cabinet", "an electrical cabinet"],
        (100, 100),
        scene_mode=scene_mode,
    )
    assert [item["bbox"] for item in result] == [[0.1, 0.1, 0.9, 0.85]]


def test_generic_near_full_frame_cabinet_alone_is_not_verified_equipment():
    result = perception.normalize_predictions(
        [[1, 1, 99, 99], [60, 40, 65, 95]],
        [0.4, 0.32],
        ["an electrical cabinet", "a concrete pole"],
        (100, 100),
        scene_mode="multiple",
    )
    assert [item["category"] for item in result] == ["pole"]


def test_generic_body_remains_supported_when_specific_inverter_text_is_occluded():
    result = perception.normalize_predictions(
        [[35, 30, 75, 80], [40, 75, 60, 95]],
        [0.36, 0.42],
        ["an electrical cabinet", "a bundle"],
        (100, 100),
        scene_mode="multiple",
    )
    assert {item["category"] for item in result} == {"cabinet", "cables"}


def test_prompt_wordpiece_evidence_does_not_turn_a_lone_verter_fragment_into_an_inverter():
    prompt = perception.PROMPT
    solar = prompt.index("solar")
    inverter = prompt.index("inverter")
    cabinet = prompt.index("cabinet")
    bundle = prompt.index("bundle")
    cables = prompt.index("cables")
    offsets = [
        (0, 0),
        (solar, solar + 5),
        (inverter, inverter + 2),
        (inverter + 2, inverter + 8),
        (cabinet, cabinet + 7),
        (bundle, bundle + 6),
        (cables, cables + 6),
    ]
    scores = perception.prompt_class_scores(
        [
            [0, 0.15, 0.08, 0.46, 0.1, 0.02, 0.01],
            [0, 0.02, 0.02, 0.02, 0.12, 0.44, 0.07],
            [0, 0.34, 0.41, 0.38, 0.12, 0.02, 0.01],
        ],
        offsets,
    )
    assert scores[0]["inverter"] == pytest.approx(0.08)
    assert scores[1]["cables"] == pytest.approx(0.44)
    assert scores[2]["inverter"] == pytest.approx(0.38)


def test_partial_person_label_is_rejected_but_generic_occluded_device_and_cables_survive():
    result = perception.normalize_predictions(
        [[1, 10, 30, 70], [40, 25, 80, 75], [45, 70, 70, 95]],
        [0.46, 0.36, 0.44],
        ["##verter", "an electrical cabinet", "a bundle"],
        (100, 100),
        scene_mode="multiple",
        class_scores=[
            {"inverter": 0.08, "cabinet": 0.1},
            {"inverter": 0.12, "cabinet": 0.36},
            {"cables": 0.44},
        ],
    )
    assert {tuple(item["bbox"]) for item in result} == {(0.4, 0.25, 0.8, 0.75), (0.45, 0.7, 0.7, 0.95)}
