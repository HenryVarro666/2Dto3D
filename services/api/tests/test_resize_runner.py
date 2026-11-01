"""Experiment controls fail before a model call and preserve failed run evidence."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image


def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3]/"scripts"))
    return importlib.import_module("resize_benchmark")


def test_resize_failures_keep_all_cases_and_return_nonzero(tmp_path, monkeypatch):
    benchmark = runner(monkeypatch)
    monkeypatch.setattr(benchmark, "verify_prepared", lambda *_: None)
    monkeypatch.setattr(benchmark, "check_file", lambda *_: None)
    protocol_path = tmp_path/"authored-protocol.json"
    protocol_path.write_text("{}")
    monkeypatch.setattr(benchmark, "PROTOCOL", protocol_path)
    calls = []

    class Worker:
        def __init__(self, **_):
            pass

        def reconstruct(self, paths, destination, progress):
            calls.append(destination.name)
            raise RuntimeError("Authored worker failure; no inference")

    monkeypatch.setattr(benchmark, "VggtReconstructor", Worker)
    args = SimpleNamespace(data_dir=tmp_path, runtime_dir=tmp_path/"runtime", runtime_root=tmp_path,
                           image_dir=tmp_path, run_name="authored-failures", reverse_order=True,
                           image_conditions=["original"], resize_modes=["isotropic"], device="cpu")
    case = {"image_condition": "original", "resize_mode": "isotropic", "inputs": [], "layout": {}}
    protocol = {"scenes": [{"id": name, "cases": [case], "reference_lengths_mm": [100]*5}
                           for name in ["first", "second"]]}
    with pytest.raises(SystemExit) as error:
        benchmark.run(args, protocol)
    assert error.value.code != 0
    assert calls == ["second-original-isotropic", "first-original-isotropic"]
    summary = json.loads((tmp_path/"runs/authored-failures/summary.json").read_text())
    assert len(summary["runs"]) == 2
    assert all(r["status"] == "failed" and "Authored worker failure" in r["error"] for r in summary["runs"])


def test_changed_tensor_is_rejected_before_any_model_worker(tmp_path, monkeypatch):
    benchmark = runner(monkeypatch)
    image = tmp_path/"authored.png"
    Image.new("RGB", (32, 16), "red").save(image)
    mask = tmp_path/"support.npy"
    np.save(mask, np.ones((518, 518), bool), allow_pickle=False)
    case = {"inputs": [{"path": image.name, "file_sha256": benchmark.sha256(image)}],
            "support_mask": mask.name, "support_mask_sha256": benchmark.sha256(mask),
            "input_preview": image.name, "input_preview_sha256": benchmark.sha256(image),
            "resize_mode": "isotropic", "input_tensor_sha256": "deliberately-wrong-hash"}
    protocol = {"configuration": benchmark.CONFIG, "e08_protocol_sha256": benchmark.sha256(benchmark.E08_PROTOCOL),
                "e08_results_sha256": benchmark.sha256(benchmark.ARCHIVE), "scenes": [{"cases": [case]}]}
    with pytest.raises(ValueError, match="RESIZE_MODEL_TENSOR_CHANGED"):
        benchmark.verify_prepared(SimpleNamespace(image_dir=tmp_path, data_dir=tmp_path), protocol)
