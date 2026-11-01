"""Publish frozen E09 metadata after checking real primary/repeat evidence."""

import argparse
import json
from pathlib import Path

import numpy as np
from public_metric_benchmark import sha256, write_json

ROOT = Path(__file__).resolve().parents[1]


def publish(data_root):
    selection_path = ROOT/"docs/measurement/resize-selection.json"
    protocol = json.loads(selection_path.read_text())
    folders = [data_root/"runs"/f"2026-11-01-e09-{round_name}" for round_name in ["primary", "repeat"]]
    paths = [p/"summary.json" for p in folders]
    primary, repeat = [json.loads(p.read_text()) for p in paths]
    assert primary["protocol_sha256"] == repeat["protocol_sha256"] == sha256(selection_path)
    assert len(primary["runs"]) == len(repeat["runs"]) == 8
    key = lambda row: (row["scene"], row["image_condition"], row["resize_mode"])
    assert len({key(r) for r in primary["runs"]}) == len({key(r) for r in repeat["runs"]}) == 8
    primary["source_run_summary_sha256"] = sha256(paths[0])
    primary["repeat_run_summary_sha256"] = sha256(paths[1])
    primary["preview_scope"] = "JPEG viewer derivatives of frozen lossless518 input tensor previews; markers use continuous source mapping"
    for row in primary["runs"]:
        other = next(r for r in repeat["runs"] if key(r) == key(row))
        assert row["status"] == other["status"] == "succeeded"
        scene = next(s for s in protocol["scenes"] if s["id"] == row["scene"])
        assert row["reference_lengths_mm"] == other["reference_lengths_mm"] == scene["reference_lengths_mm"]
        name = "-".join(key(row))
        with np.load(folders[0]/name/"geometry.npz", allow_pickle=False) as a, np.load(folders[1]/name/"geometry.npz", allow_pickle=False) as b:
            row["repeat_arrays_equal"] = a.files == b.files and all(np.array_equal(a[k], b[k]) for k in a.files)
        row["repeat_geometry_matches"] = row["geometry_sha256"] == other["geometry_sha256"]
        row["repeat_raw_cloud_matches"] = row["raw_cloud_sha256"] == other["raw_cloud_sha256"]
        row["repeat_input_tensor_matches"] = row["input_tensor_sha256"] == other["input_tensor_sha256"]
        assert [c["segment_id"] for c in row["checks"]] == [c["segment_id"] for c in other["checks"]]
        row["repeat_max_distance_delta_mm"] = max(abs(a["calibrated_mm"]-b["calibrated_mm"])
                                                  for a, b in zip(row["checks"], other["checks"], strict=True))
        row["repeat_worker_wall_ms"] = other["worker_wall_ms"]
    write_json(ROOT/"docs/measurement/resize-results.json", primary)
    write_json(ROOT/"docs/measurement/resize-repeat.json", repeat)
    print("Published E09; repeat matches:", all(r["repeat_arrays_equal"] and r["repeat_geometry_matches"] and
          r["repeat_raw_cloud_matches"] and r["repeat_input_tensor_matches"] and r["repeat_max_distance_delta_mm"] == 0 for r in primary["runs"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data/measurement-resize")
    publish(parser.parse_args().data_dir.resolve())
