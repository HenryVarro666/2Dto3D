import numpy as np
import pytest
from pv3d import undistortion as und
from pv3d.metric_benchmark import camera_project, camera_ray

PARAMS = [100, 100, 50, 40, .2, .15, -.0002, -.0003, -.03, .3, .001, .001]


def test_vector_fisheye_projection_matches_independently_used_scalar_equations():
    rays = np.array([[0, 0], [.2, -.3], [-.5, .7], [.8, .6]])
    expected = np.stack([camera_project(ray, PARAMS) for ray in rays])
    np.testing.assert_allclose(und.project_fisheye(rays, PARAMS), expected, atol=1e-10)


def test_full_field_camera_contains_source_boundary_and_fixed_physical_point_roundtrips():
    k = und.full_field_camera(PARAMS, [100, 80], samples=65)
    for xy in [[0, 0], [99, 0], [0, 79], [99, 79], [19, 37], [82, 61]]:
        ray = camera_ray(np.array(xy)+.5, PARAMS)
        pixel = und.project_pinhole(ray * 2, k)
        assert (np.array(pixel) >= 0).all() and (np.array(pixel) <= [99, 79]).all()
        np.testing.assert_allclose(und.pinhole_to_source(pixel, PARAMS, k), xy, atol=1e-8)


def test_off_axis_mapping_has_no_shared_half_pixel_shift():
    params = [100, 100, 50, 40, 0, 0, 0, 0, 0, 0, 0, 0]
    k = np.array([[100, 0, 50], [0, 100, 40], [0, 0, 1]])
    target = [100*np.tan(.2)+50-.5, 40-.5]
    np.testing.assert_allclose(und.pinhole_to_source(target, params, k), [69.5, 39.5], atol=1e-10)


def test_identity_opencv_remap_keeps_an_off_axis_pixel_exact():
    rgb = np.arange(9*7*3, dtype=np.uint8).reshape(7, 9, 3)
    yy, xx = np.indices(rgb.shape[:2])
    mapped = und.remap_rgb(rgb, np.stack((xx, yy), axis=-1))
    np.testing.assert_array_equal(mapped, rgb)


def test_bilinear_camera_z_uses_fixed_fractional_grid_and_extrinsic_world_frame():
    yy, xx = np.indices((5, 5))
    depth = 2 + .1*xx + .2*yy
    k = np.array([[2, 0, 1], [0, 4, 2], [0, 0, 1]], float)
    r = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], float)
    t = np.array([1, 2, 3])
    geometry = {"depth": depth[None], "confidence": np.ones((1, 5, 5)),
                "intrinsics": k[None], "extrinsics": np.column_stack((r, t))[None],
                "rects": np.array([[0, 0, 5, 5]])}
    pixel = [1.25, 2.75]
    sample = und.sample_camera_depth(geometry, pixel, support_mask=np.ones((5, 5), bool))
    z = 2 + .1*pixel[0] + .2*pixel[1]
    camera_xyz = np.array([(pixel[0]-1)/2*z, (pixel[1]-2)/4*z, z])
    assert sample["depth_z"] == pytest.approx(z)
    assert sample["grid_xy"] == pixel
    assert sum(p["weight"] for p in sample["neighbours"]) == pytest.approx(1)
    np.testing.assert_allclose(sample["world_xyz"], r.T @ (camera_xyz-t))


def test_resize_support_mask_conservatively_rejects_border_and_hole_footprints():
    valid = np.ones((64, 64), bool)
    valid[32, 32] = False
    mask = und.model_support_mask(valid, [0, 2, 32, 34], 36)
    assert mask.shape == (36, 36)
    assert not mask[0, 10] and not mask[2, 0] and not mask[18, 16]
    assert mask[10, 8]


def test_sampling_rejects_missing_depth_and_invalid_corrected_neighbour_support():
    geometry = {"depth": np.ones((1, 5, 5)), "confidence": np.ones((1, 5, 5)),
                "intrinsics": np.eye(3)[None], "extrinsics": np.eye(4)[None, :3],
                "rects": np.array([[1, 1, 4, 4]])}
    support = np.ones((5, 5), bool); support[2, 2] = False
    with pytest.raises(ValueError, match="INVALID_IMAGE_SUPPORT"):
        und.sample_camera_depth(geometry, [1.5, 1.5], support_mask=support)
    geometry["depth"][0, 2, 2] = np.nan
    with pytest.raises(ValueError, match="INVALID_PREDICTED_DEPTH"):
        und.sample_camera_depth(geometry, [1.5, 1.5], support_mask=np.ones((5, 5), bool))
    with pytest.raises(ValueError, match="OUTSIDE_CONTENT"):
        und.sample_camera_depth(geometry, [.5, 1.5], support_mask=np.ones((5, 5), bool))


def test_integer_grid_unprojection_matches_authored_raw_model_point_without_extra_half_pixel():
    k = np.array([[2, 0, 1], [0, 4, 2], [0, 0, 1]], float)
    e = np.array([[0, -1, 0, 1], [1, 0, 0, 2], [0, 0, 1, 3]], float)
    camera, world = und.unproject_depth([3, 1], 4, k, e)
    np.testing.assert_allclose(camera, [4, -1, 4])
    np.testing.assert_allclose(world, [-3, -3, 1])


def test_known_pinhole_intrinsics_map_to_integer_centre_model_grid():
    k = np.array([[100, 0, 50], [0, 100, 40], [0, 0, 1]], float)
    grid_k = und.grid_camera_matrix(k, [0, 4, 50, 44], [100, 80])
    result = grid_k @ [.4, .2, 2]
    np.testing.assert_allclose(result[:2]/result[2], [34.5, 28.5])
