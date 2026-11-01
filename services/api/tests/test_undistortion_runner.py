"""A failed model worker must preserve evidence and fail the experiment command."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_failed_workers_preserve_every_case_and_exit_nonzero(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "scripts"))
    benchmark = importlib.import_module("undistortion_benchmark")
    monkeypatch.setattr(benchmark, "verify_prepared", lambda *_: None)
    monkeypatch.setattr(benchmark, "check_file", lambda *_: None)
    calls = []

    class FailedWorker:
        def __init__(self, **_):
            pass

        def reconstruct(self, paths, destination, progress):
            calls.append(destination.name)
            raise RuntimeError("Authored worker failure; no model executed")

    monkeypatch.setattr(benchmark, "VggtReconstructor", FailedWorker)
    args = SimpleNamespace(data_dir=tmp_path, runtime_dir=tmp_path / "runtime",
                           runtime_root=tmp_path, run_name="authored-failure",
                           conditions=["original"], device="cpu")
    protocol = {"scenes": [{"id": name, "reference_lengths_mm": [100]*5,
                            "conditions": {"original": {"inputs": []}}}
                           for name in ["first", "second"]]}
    with pytest.raises(SystemExit) as error:
        benchmark.run(args, protocol)
    assert error.value.code != 0
    summary = json.loads((tmp_path / "runs/authored-failure/summary.json").read_text())
    assert calls == ["first-original", "second-original"]
    assert len(summary["runs"]) == 2
    assert all(r["status"] == "failed" and "Authored worker failure" in r["error"]
               for r in summary["runs"])
