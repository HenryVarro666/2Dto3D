"""Publish E10-M only after complete fixed-protocol primary and repeat audits."""

import argparse
import json
from pathlib import Path

import numpy as np
from public_metric_benchmark import sha256, write_json

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/"docs/measurement/independent-selection.json"
SOURCES = ROOT/"docs/measurement/independent-sources.json"
RESULTS = ROOT/"docs/measurement/independent-results.json"
REPEAT = ROOT/"docs/measurement/independent-repeat.json"


def key(row):
    return row["scene"], row["image_condition"], row["resize_mode"]


def validate_round(summary, protocol, fingerprint):
    expected = {(s["id"], c["image_condition"], c["resize_mode"])
                for s in protocol["scenes"] for c in s["cases"]}
    if len(summary["runs"]) != len(expected) or {key(r) for r in summary["runs"]} != expected:
        raise ValueError("INDEPENDENT_CASE_SET_INCOMPLETE_OR_DUPLICATE")
    if summary["protocol_sha256"] != fingerprint:
        raise ValueError("INDEPENDENT_PROTOCOL_CHANGED")
    for row in summary["runs"]:
        scene = next(s for s in protocol["scenes"] if s["id"] == row["scene"])
        case = next(c for c in scene["cases"] if
                    (c["image_condition"], c["resize_mode"]) == (row["image_condition"], row["resize_mode"]))
        model = row.get("model", {})
        if (model.get("image_condition") != row["image_condition"]
            or row.get("input_tensor_sha256") != case["input_tensor_sha256"]
            or row.get("layout") != case["layout"]):
            raise ValueError("INDEPENDENT_INPUT_CASE_CHANGED")
        if (row["status"] != "succeeded" or row["input_size"] != 518 or row["view_count"] != 3
            or model.get("revision") != protocol["model_revision"]
            or model.get("code_revision") != protocol["model_code_revision"]
            or model.get("protocol_sha256") != fingerprint or model.get("resize_mode") != row["resize_mode"]):
            raise ValueError("INDEPENDENT_MODEL_OR_FAILED_CASE")
        if row["reference_lengths_mm"] != scene["reference_lengths_mm"] or row["calibration"]["known_length_mm"] != scene["reference_lengths_mm"][0]:
            raise ValueError("INDEPENDENT_REFERENCE_CHANGED")
        scale, calibration_distance = row["calibration"]["mm_per_unit"], row["calibration"]["distance_units"]
        if (not np.isfinite([scale, calibration_distance]).all() or min(scale, calibration_distance) <= 0
            or not np.isclose(scale*calibration_distance, scene["reference_lengths_mm"][0], atol=1e-8, rtol=1e-10)):
            raise ValueError("INDEPENDENT_INCONSISTENT_ERROR: calibration scale")
        if len(row["checks"]) != 4 or [c["segment_id"] for c in row["checks"]] != [s["id"] for s in scene["segments"][1:]]:
            raise ValueError("INDEPENDENT_CHECK_SET_CHANGED")
        for i, check in enumerate(row["checks"], 1):
            if check["reference_mm"] != scene["reference_lengths_mm"][i]:
                raise ValueError("INDEPENDENT_REFERENCE_CHANGED")
            values = [check["calibrated_mm"], check["relative_error_pct"]]
            if not np.isfinite(values).all() or values[0] <= 0 or values[1] < 0:
                raise ValueError("INDEPENDENT_NONFINITE_RESULT")
            absolute = abs(check["calibrated_mm"]-check["reference_mm"])
            error = absolute/check["reference_mm"]*100
            if (not np.isclose(check["relative_error_pct"], error, atol=1e-8, rtol=1e-10)
                or not np.isclose(check["absolute_error_mm"], absolute, atol=1e-8, rtol=1e-10)
                or not np.isclose(check["relative_distance_u"]*scale, check["calibrated_mm"], atol=1e-8, rtol=1e-10)):
                raise ValueError("INDEPENDENT_INCONSISTENT_ERROR")


def publish(data_root, runtime, check_only=False):
    protocol = json.loads(PROTOCOL.read_text())
    assert protocol["source_selection_sha256"] == sha256(SOURCES)
    folders = [data_root/"runs"/f"2026-11-01-e10m-{r}" for r in ["primary", "repeat"]]
    summaries = [json.loads((p/"summary.json").read_text()) for p in folders]
    primary, repeat = summaries
    for summary in summaries:
        validate_round(summary, protocol, sha256(PROTOCOL))
    assert primary["order_reversed"] is False and repeat["order_reversed"] is True
    assert [key(r) for r in primary["runs"]] == list(reversed([key(r) for r in repeat["runs"]]))
    source = json.loads(SOURCES.read_text())
    primary["source_run_summary_sha256"] = sha256(folders[0]/"summary.json")
    primary["repeat_run_summary_sha256"] = sha256(folders[1]/"summary.json")
    primary["source_selection_sha256"] = sha256(SOURCES)
    primary["independence_scope"] = source["independence_scope"]
    primary["source_gallery"] = []
    for scene in source["scenes"]:
        first = next(r for r in primary["runs"] if key(r) == (scene["id"], "original", "legacy14"))
        job = json.loads((runtime/"multiview"/first["job_id"]/"result.json").read_text())
        primary["source_gallery"].append({"scene": scene["id"], "views": [
            {"filename": Path(source_view["path"]).name, "image_url": asset["image_url"],
             "original_jpeg_sha256": source_view["sha256"]}
            for source_view, asset in zip(scene["views"], job["views"], strict=True)]})
    for row in primary["runs"]:
        other = next(r for r in repeat["runs"] if key(r) == key(row))
        name = "-".join(key(row))
        with np.load(folders[0]/name/"geometry.npz", allow_pickle=False) as a, np.load(folders[1]/name/"geometry.npz", allow_pickle=False) as b:
            row["repeat_arrays_equal"] = a.files == b.files and all(np.array_equal(a[k], b[k]) for k in a.files)
        for field in ["geometry_sha256", "raw_cloud_sha256", "input_tensor_sha256"]:
            row["repeat_"+field+"_equal"] = row[field] == other[field]
        row["repeat_max_distance_delta_mm"] = max(abs(a["calibrated_mm"]-b["calibrated_mm"])
                                                  for a, b in zip(row["checks"], other["checks"], strict=True))
        row["repeat_worker_wall_ms"] = other["worker_wall_ms"]
    primary["repeat_exact"] = all(r["repeat_arrays_equal"] and r["repeat_geometry_sha256_equal"]
                                   and r["repeat_raw_cloud_sha256_equal"] and r["repeat_input_tensor_sha256_equal"]
                                   and r["repeat_max_distance_delta_mm"] == 0 for r in primary["runs"])
    if check_only:
        if json.loads(RESULTS.read_text()) != primary or json.loads(REPEAT.read_text()) != repeat:
            raise ValueError("PUBLISHED_INDEPENDENT_EVIDENCE_CHANGED")
    else:
        write_json(RESULTS, primary)
        write_json(REPEAT, repeat)
    print(f"E10-M:12 scene/policy cases ×4 held-outs verified; repeat exact={primary['repeat_exact']}; sources and all regressions retained")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data/measurement-independent")
    parser.add_argument("--runtime-dir", type=Path, default=ROOT/"data/measurement-public/runtime")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    publish(args.data_dir.resolve(), args.runtime_dir.resolve(), args.check)
