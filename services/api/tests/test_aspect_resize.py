"""Controlled preprocessing geometry; no model or external photos required."""

import json
import sys

import numpy as np
import pytest
from PIL import Image
from pv3d import reconstruction as rec
from pv3d.metric_benchmark import grid_to_photo, photo_to_grid
from pv3d.undistortion import grid_camera_matrix, model_support_mask


@pytest.mark.parametrize("size", [(6048, 4032), (4032, 6048), (641, 315), (1300, 1)])
def test_isotropic_layout_preserves_one_scale_and_covers_fractional_content(size):
    layout = rec.image_layout(*size, 518, "isotropic")
    rect, mapped = np.asarray(layout["rect"]), np.asarray(layout["mapping_rect"])
    scale = 518 / max(size)
    np.testing.assert_allclose((mapped[2:]-mapped[:2])/size, [scale, scale], atol=1e-15)
    np.testing.assert_allclose(mapped[:2]+mapped[2:], [518, 518], atol=1e-12)
    assert (rect[:2] <= mapped[:2]).all() and (rect[2:] >= mapped[2:]).all()
    assert (mapped[:2]-rect[:2] < 1).all() and (rect[2:]-mapped[2:] < 1).all()
    if size == (6048, 4032):
        assert rect.tolist() == [0, 86, 518, 432]
        np.testing.assert_allclose(mapped, [0, 259/3, 518, 1295/3], atol=1e-12)
    source = np.asarray([size[0]*.371-.5, size[1]*.613-.5])
    grid = photo_to_grid(source, mapped, size)
    np.testing.assert_allclose(grid, (source+.5)*scale+mapped[:2]-.5, atol=1e-12)
    np.testing.assert_allclose(grid_to_photo(grid, mapped, size), source, atol=1e-10)


def test_default_and_explicit_legacy_pixels_remain_identical_to_previous_algorithm(tmp_path):
    rgb = np.random.default_rng(7).integers(0, 256, (315, 641, 3), dtype=np.uint8)
    path = tmp_path / "authored.png"
    Image.fromarray(rgb).save(path)
    old = Image.fromarray(rgb).resize((518, 252), Image.Resampling.BICUBIC)
    square = Image.new("RGB", (518, 518), "white")
    square.paste(old, (0, 133))
    expected = np.asarray(square, dtype=np.float32).transpose(2, 0, 1)/255
    for mode in [None, "legacy14"]:
        args = {} if mode is None else {"resize_mode": mode}
        images, rects = rec.prepare_images([path], 518, **args)
        np.testing.assert_array_equal(images[0], expected)
        assert rects.tolist() == [[0, 133, 518, 385]]


def test_isotropic_pixels_follow_inverse_affine_not_integer_height_stretch(tmp_path):
    width, height, target = 700, 330, 224
    yy, xx = np.indices((height, width))
    rgb = np.stack((20+200*(xx+.5)/width, 20+200*(yy+.5)/height, np.full_like(xx, 100)), axis=-1)
    path = tmp_path / "authored-ramp.png"
    Image.fromarray(np.rint(rgb).astype(np.uint8)).save(path)
    images, rects = rec.prepare_images([path], target, resize_mode="isotropic")
    assert images.shape == (1, 3, target, target)
    scale, offset_y = target/width, (target-height*target/width)/2
    for x, y in [(40, 90), (150, 130)]:
        source_center = np.array([x+.5, y+.5-offset_y])/scale
        expected = [20+200*source_center[0]/width, 20+200*source_center[1]/height, 100]
        np.testing.assert_allclose(images[0, :, y, x]*255, expected, atol=1.05)
    assert (images[0, :, :int(rects[0, 1])] == 1).all()


def test_fractional_support_uses_actual_inverse_mapping_and_full_bicubic_footprint():
    width, height, target = 191, 117, 224
    valid = np.ones((height, width), bool)
    valid[35:60, 55:90] = False
    layout = rec.image_layout(width, height, target, "isotropic")
    rect, mapped = layout["rect"], layout["mapping_rect"]
    mask = model_support_mask(valid, rect, target, mapping_rect=mapped)
    scale = target/width
    radius = int(np.ceil(2/scale))+2
    points = np.argwhere(mask)
    assert len(points) > 1000
    for y, x in points[::31]:
        px, py = np.rint((np.array([x, y])+.5-mapped[:2])/scale-.5).astype(int)
        assert radius <= px < width-radius and radius <= py < height-radius
        assert valid[py-radius:py+radius+1, px-radius:px+radius+1].all()
    assert not mask[:rect[1]].any() and not mask[rect[3]:].any()


def test_known_camera_rays_preserve_half_pixel_at_fractional_letterbox():
    layout = rec.image_layout(6048, 4032, 518, "isotropic")
    photo_k = np.array([[3300, 0, 3020], [0, 3400, 2020], [0, 0, 1]])
    k = grid_camera_matrix(photo_k, layout["mapping_rect"], [6048, 4032])
    ray = np.array([.3, -.2, 1.])
    photo_corner = photo_k @ ray
    grid = photo_to_grid(photo_corner[:2]-.5, layout["mapping_rect"], [6048, 4032])
    np.testing.assert_allclose(np.linalg.solve(k, [*grid, 1]), ray, atol=1e-12)


def test_resize_mode_is_forwarded_to_isolated_worker_and_unknown_mode_is_rejected(tmp_path):
    worker = tmp_path / "worker.py"
    worker.write_text('raise SystemExit(2)\n')
    model = rec.VggtReconstructor(runtime_python=sys.executable, worker_script=worker,
                                  resize_mode="isotropic")
    output = tmp_path / "failure"
    with pytest.raises(RuntimeError, match="worker failed"):
        model.reconstruct([tmp_path/"a.png"], output, lambda _: None)
    assert json.loads((output/"input.json").read_text())["resize_mode"] == "isotropic"
    with pytest.raises(ValueError, match="resize"):
        rec.VggtReconstructor(resize_mode="unknown")
