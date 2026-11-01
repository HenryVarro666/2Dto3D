import numpy as np
import pytest

from pv3d import metric_benchmark as metric


def test_fisheye_ray_uses_perspective_z_not_euclidean_range():
    params = [100, 100, 50, 50, 0, 0, 0, 0, 0, 0, 0, 0]
    # An undistorted ray x/z=1 maps to theta=pi/4 in fisheye coordinates.
    pixel = [50 + 100 * np.pi / 4, 50]
    ray = metric.camera_ray(pixel, params)
    np.testing.assert_allclose(ray, [1, 0, 1], atol=1e-10)


def test_real_camera_distortion_roundtrips_off_axis_pixel():
    params = [3430.27, 3429.23, 3032.95, 2003.59, .218983, .155576,
              -.000274629, -.000387159, -.0364669, .302935, .00133613, .00101227]
    ray = metric.camera_ray([1000.5, 3000.5], params)
    np.testing.assert_allclose(metric.camera_project(ray[:2], params), [1000.5, 3000.5], atol=1e-7)


def test_letterbox_inverse_preserves_pixel_centers():
    # One output pixel spans 18 original pixels; image top is at grid y=56.
    assert metric.grid_to_photo([0, 56], [0, 56, 336, 280], [6048, 4032]) == [8.5, 8.5]
    assert metric.photo_to_grid([8.5, 8.5], [0, 56, 336, 280], [6048, 4032]) == [0, 56]


def test_reference_sampling_records_pixel_shift_and_rejects_depth_edges():
    depth = np.full((25, 25), 2, np.float32)
    params = [100, 100, 12.5, 12.5, 0, 0, 0, 0, 0, 0, 0, 0]
    point = metric.reference_point(depth, [12, 12], params)
    np.testing.assert_allclose(point["xyz_m"], [0, 0, 2])
    assert point["sample_shift_px"] == 0
    assert point["support_count"] >= 121
    depth[:, 13:] = 3
    with pytest.raises(ValueError, match="DEPTH_DISCONTINUITY"):
        metric.reference_point(depth, [12, 12], params)


def test_reference_sampling_never_fills_missing_depth():
    depth = np.full((25, 25), np.inf, np.float32)
    params = [100, 100, 12.5, 12.5, 0, 0, 0, 0, 0, 0, 0, 0]
    with pytest.raises(ValueError, match="INSUFFICIENT_REFERENCE_DEPTH"):
        metric.reference_point(depth, [12, 12], params)


def test_sparse_laser_reference_uses_support_neighbourhood_without_filling_holes():
    depth = np.full((25, 25), np.inf, np.float32)
    depth[::3, ::3] = 2
    params = [100, 100, 12.5, 12.5, 0, 0, 0, 0, 0, 0, 0, 0]
    point = metric.reference_point(depth, [12, 12], params)
    assert point["support_count"] == 49
    assert point["sample_pixel_xy"] == [12, 12]


def test_raw_depth_is_binary_float_dump_not_jpeg(tmp_path):
    path = tmp_path / "DSC_0001.JPG"
    np.array([[1, 2], [3, np.inf]], dtype="<f4").tofile(path)
    assert metric.read_depth(path, 2, 2)[1, 0] == 3
    with pytest.raises(ValueError, match="DEPTH_BYTE_COUNT"):
        metric.read_depth(path, 3, 2)
