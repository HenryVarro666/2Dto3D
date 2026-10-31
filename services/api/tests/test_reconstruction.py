"""Geometry image mapping and isolated-process failures; no model downloads."""

import sys

import numpy as np
import pytest
from PIL import Image
from pv3d import reconstruction


def test_letterbox_keeps_entire_photo_and_records_pixel_mapping(tmp_path):
    paths = []
    for index, size in enumerate([(400, 200), (200, 400)]):
        path = tmp_path / f"{index}.png"
        Image.new("RGB", size, "#ff0000").save(path)
        paths.append(path)
    images, rects = reconstruction.prepare_images(paths, 224)
    assert images.shape == (2, 3, 224, 224)
    assert rects.tolist() == [[0, 56, 224, 168], [56, 0, 168, 224]]
    assert images[0, :, 80, 10].tolist() == [1, 0, 0]
    assert images[0, :, 10, 10].tolist() == [1, 1, 1]
    assert reconstruction.photo_to_grid([0.25, 0.75], rects[0]).tolist() == [56, 140]


def test_geometry_loader_checks_array_dimensions_and_camera_finiteness(tmp_path):
    path = tmp_path / "geometry.npz"
    shape = (2, 14, 14)
    arrays = {
        "points": np.zeros((*shape, 3), np.float32),
        "depth": np.ones(shape, np.float32),
        "confidence": np.ones(shape, np.float32),
        "colors": np.zeros((*shape, 3), np.uint8),
        "rects": np.array([[0, 0, 14, 14]] * 2),
        "extrinsics": np.tile(np.eye(4, dtype=np.float32)[:3], (2, 1, 1)),
        "intrinsics": np.tile(np.eye(3, dtype=np.float32), (2, 1, 1)),
    }
    np.savez_compressed(path, **arrays)
    assert reconstruction.load_geometry(path, 2)["points"].shape == (*shape, 3)
    with pytest.raises(ValueError):
        reconstruction.load_geometry(path, 3)
    arrays["intrinsics"][0, 0, 0] = np.nan
    np.savez_compressed(path, **arrays)
    with pytest.raises(ValueError, match="camera"):
        reconstruction.load_geometry(path, 2)


def test_subprocess_stage_is_reported_and_failure_preserves_local_log(tmp_path):
    worker = tmp_path / "failing_worker.py"
    worker.write_text(
        'import sys\nprint(\'{"stage":"estimating_geometry"}\',flush=True)\n'
        'print("private worker details",file=sys.stderr)\nraise SystemExit(2)\n'
    )
    model = reconstruction.VggtReconstructor(runtime_python=sys.executable, worker_script=worker)
    seen = []
    output = tmp_path / "job"
    with pytest.raises(RuntimeError, match="worker failed"):
        model.reconstruct([tmp_path / "a.jpg", tmp_path / "b.jpg"], output, seen.append)
    assert "estimating_geometry" in seen
    assert "private worker details" in (output / "worker.log").read_text()


def test_missing_runtime_has_actionable_error_and_invalid_startup_settings_are_rejected(tmp_path):
    model = reconstruction.VggtReconstructor(runtime_python=tmp_path / "missing")
    assert model.status()["state"] == "not_installed"
    with pytest.raises(RuntimeError, match="setup-multiview"):
        model.reconstruct([], tmp_path / "out", lambda _stage: None)
    with pytest.raises(ValueError):
        reconstruction.VggtReconstructor(input_size=100)
    with pytest.raises(ValueError):
        reconstruction.VggtReconstructor(device="remote")
