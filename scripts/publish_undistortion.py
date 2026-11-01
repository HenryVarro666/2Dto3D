"""Publish compact E08 metadata and local preview references, never raw photos."""

import argparse
import json
from pathlib import Path

from public_metric_benchmark import sha256, write_json

ROOT = Path(__file__).resolve().parents[1]


def publish(data_root, runtime):
    protocol_path = ROOT/"docs/measurement/undistortion-selection.json"
    protocol = json.loads(protocol_path.read_text())
    primary_path = data_root/"runs/2026-11-01-e08-primary/summary.json"
    repeat_path = data_root/"runs/2026-11-01-e08-repeat/summary.json"
    primary, repeat = [json.loads(p.read_text()) for p in [primary_path, repeat_path]]
    assert all(r["status"] != "running" for s in [primary, repeat] for r in s["runs"])
    assert primary["protocol_sha256"] == repeat["protocol_sha256"] == sha256(protocol_path)
    primary["source_run_summary_sha256"] = sha256(primary_path)
    primary["repeat_run_summary_sha256"] = sha256(repeat_path)
    primary["preview_scope"] = "JPEG viewer previews with fixed scanner-point projections; model inputs are lossless"
    for row in primary["runs"]:
        scene = next(s for s in protocol["scenes"] if s["id"] == row["scene"])
        counterpart = next(r for r in repeat["runs"]
                           if (r["scene"], r["condition"]) == (row["scene"], row["condition"]))
        row["repeat_status"] = counterpart["status"]
        if row["status"] != "succeeded" or counterpart["status"] != "succeeded":
            row["repeat_geometry_matches"] = False
            continue
        assert row["reference_lengths_mm"] == scene["reference_lengths_mm"]
        assert counterpart["reference_lengths_mm"] == scene["reference_lengths_mm"]
        row["repeat_geometry_matches"] = row["geometry_sha256"] == counterpart["geometry_sha256"]
        row["repeat_max_distance_delta_mm"] = max(abs(a["calibrated_mm"]-b["calibrated_mm"])
                                                  for a, b in zip(row["checks"], counterpart["checks"], strict=True))
        result = json.loads((runtime/"multiview"/row["job_id"]/"result.json").read_text())
        row["preview_image_url"] = result["views"][0]["image_url"]
        width, height = scene["camera"]["size"]
        row["preview_size"] = [width, height]
        row["preview_points"] = [{"id": chr(65+i), "uv": [(p["photo_xy"][0]+.5)/width,
                    (p["photo_xy"][1]+.5)/height]} for i, p in
                    enumerate(scene["conditions"][row["condition"]]["point_mappings"])]
        row["photo_invalid_fraction"] = scene["conditions"][row["condition"]]["photo_invalid_fraction"]
        row["repeat_worker_wall_ms"] = counterpart["worker_wall_ms"]
    write_json(ROOT/"docs/measurement/undistortion-results.json", primary)
    write_json(ROOT/"docs/measurement/undistortion-repeat.json", repeat)
    print("Published E08 primary, repeat and fixed-point preview metadata")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data/measurement-undistortion")
    parser.add_argument("--runtime-dir", type=Path, default=ROOT/"data/measurement-public/runtime")
    options = parser.parse_args()
    publish(options.data_dir.resolve(), options.runtime_dir.resolve())
