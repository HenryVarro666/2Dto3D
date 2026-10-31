"""Geometry tests use analytic two-camera planes, never model-quality doubles."""

import json
import struct

import numpy as np
import pytest
from PIL import Image
from pv3d.pointcloud import build_pointcloud, export_pointcloud
from pv3d.store import Store


def geometry():
    y, x = np.mgrid[:10, :10]
    first = np.stack([x / 10, y / 10, np.ones_like(x)], axis=-1).astype(np.float32)
    second = first.copy()
    second[..., 0] += 0.1
    extrinsics = np.tile(np.eye(4, dtype=np.float32)[:3], (2, 1, 1))
    extrinsics[1, 0, 3] = -0.1
    return {
        "points": np.stack([first, second]),
        "depth": np.ones((2, 10, 10), np.float32),
        "confidence": np.ones((2, 10, 10), np.float32),
        "colors": np.stack([np.full((10, 10, 3), [255, 0, 0], np.uint8),
                            np.full((10, 10, 3), [0, 0, 255], np.uint8)]),
        "rects": np.array([[0, 0, 10, 10]] * 2),
        "extrinsics": extrinsics,
        "intrinsics": np.tile(np.diag([10, 10, 1]).astype(np.float32), (2, 1, 1)),
    }


def assets():
    return [{"id": str(i) * 32, "width": 10, "height": 10} for i in (1, 2)]


def observation(identifier, view, box, component_id=None):
    return {"id": identifier, "asset_id": assets()[view]["id"], "bbox": box,
            "category": "cabinet", "label": "Cabinet", "source": "grounding_dino", "score": 0.7,
            "component_id": component_id}


def test_filter_padding_invalid_depth_confidence_and_y_up_rgb(tmp_path):
    data = geometry()
    data["rects"][:] = [2, 2, 8, 8]
    data["points"][0, 3, 3] = np.nan
    data["depth"][0, 4, 4] = -1
    data["confidence"][1, 5, 5] = np.nan
    cloud = build_pointcloud(data, assets(), [], Store(tmp_path), automatic=True)
    assert 0 < len(cloud["vertices"]) < 72
    assert np.isfinite(cloud["vertices"]).all()
    assert np.all(cloud["vertices"][:, 1:] < 0)  # OpenCV -> Three Y-up once
    assert np.min(cloud["vertices"][:, 0]) >= 0.2
    assert cloud["quality"]["retained_per_view"] == [34, 35]
    overlap = np.argmin(np.linalg.norm(cloud["vertices"] - [0.5, -0.3, -1], axis=1))
    assert np.allclose(cloud["colors"][overlap], [128, 0, 128], atol=1)
    assert cloud["quality"]["metric_scale_status"] == "unknown"


def test_same_category_cross_view_match_never_merges_neighbors_in_one_view(tmp_path):
    obs = [observation("a", 0, [0, 0.2, 0.45, 0.8]),
           observation("b", 1, [0, 0.2, 0.35, 0.8]),
           observation("c", 0, [0.6, 0.2, 1, 0.8])]
    cloud = build_pointcloud(geometry(), assets(), obs, Store(tmp_path), automatic=True)
    by_id = {o["id"]: o["component_id"] for o in cloud["observations"]}
    assert by_id["a"] == by_id["b"] != by_id["c"]
    assert len(cloud["components"]) == 2
    assert all(c["point_count"] > 0 for c in cloud["components"])


def test_explicit_manual_link_and_split_preserve_ids(tmp_path):
    obs = [observation("a", 0, [0, 0.2, 0.45, 0.8], "part-linked"),
           observation("b", 1, [0, 0.2, 0.35, 0.8], "part-linked")]
    store = Store(tmp_path)
    linked = build_pointcloud(geometry(), assets(), obs, store, automatic=False)
    assert [c["id"] for c in linked["components"]] == ["part-linked"]
    obs[1]["component_id"] = "part-split"
    split = build_pointcloud(geometry(), assets(), obs, store, automatic=False)
    assert {c["id"] for c in split["components"]} == {"part-linked", "part-split"}


def test_authoritative_png_preserves_holes_and_disjoint_islands(tmp_path):
    store = Store(tmp_path)
    ref_id = "a" * 32
    folder = tmp_path / "refinements" / ref_id
    folder.mkdir()
    mask = np.zeros((10, 10), np.uint8)
    mask[1:5, 1:5] = 255
    mask[2:4, 2:4] = 0
    mask[7:9, 7:9] = 255
    Image.fromarray(mask).save(folder / "binary-mask.png")
    store.add_asset({**assets()[0], "sha256": "test-photo"})
    store.add_refinement({"id": ref_id, "asset_id": assets()[0]["id"]})
    data = geometry()
    data["confidence"][1] = 0
    obs = observation("a", 0, [0, 0, 1, 1], "part-mask")
    obs["refinement_id"] = ref_id
    cloud = build_pointcloud(data, assets(), [obs], store, automatic=False)
    assert cloud["components"][0]["point_count"] == 16
    assert cloud["context_point_count"] == 84


def test_empty_geometry_is_reviewable_and_exports_no_fake_cloud(tmp_path):
    data = geometry()
    data["depth"][:] = 0
    cloud = build_pointcloud(data, assets(), [], Store(tmp_path), automatic=True)
    assert cloud["quality"]["needs_review"]
    assert len(cloud["vertices"]) == 0
    assert export_pointcloud(cloud, tmp_path) is False
    assert not (tmp_path / "cloud.glb").exists()


def test_glb_native_points_ids_and_ply_component_mapping(tmp_path):
    obs = [observation("a", 0, [0.1, 0.2, 0.5, 0.8], "part-kept")]
    cloud = build_pointcloud(geometry(), assets(), obs, Store(tmp_path), automatic=False)
    assert export_pointcloud(cloud, tmp_path)
    raw = (tmp_path / "cloud.glb").read_bytes()
    length = struct.unpack_from("<I", raw, 12)[0]
    header = json.loads(raw[20:20 + length])
    assert all(p["mode"] == 0 for m in header["meshes"] for p in m["primitives"])
    assert {n.get("extras", {}).get("component_id") for n in header["nodes"]} >= {"part-kept", "__context__"}
    assert header["asset"]["extras"]["metric_scale_status"] == "unknown"
    ply = (tmp_path / "cloud.ply").read_bytes()
    assert b"property uint component_index" in ply
    mapping = json.loads((tmp_path / "component-map.json").read_text())
    assert mapping == {"0": "__context__", "1": "part-kept"}


def test_transitive_matches_do_not_merge_two_observations_in_the_same_view(tmp_path):
    obs = [observation("a", 0, [0, 0.2, 0.6, 0.8]),
           observation("b", 1, [0, 0.2, 1, 0.8]),
           observation("c", 0, [0.4, 0.2, 1, 0.8])]
    cloud = build_pointcloud(geometry(), assets(), obs, Store(tmp_path), automatic=True)
    ids = {o["id"]: o["component_id"] for o in cloud["observations"]}
    assert ids["a"] != ids["c"] and ids["b"] in {ids["a"], ids["c"]}


def test_export_cap_is_deterministic_and_keeps_a_small_component(tmp_path):
    data = geometry()
    rng = np.random.default_rng(42)
    data.update(points=rng.random((2, 400, 400, 3), dtype=np.float32),
                depth=np.ones((2, 400, 400), np.float32),
                confidence=np.ones((2, 400, 400), np.float32),
                colors=np.full((2, 400, 400, 3), 128, np.uint8),
                rects=np.array([[0, 0, 400, 400]] * 2))
    obs = [observation("tiny", 0, [0, 0, 0.1, 0.1], "part-small")]
    store = Store(tmp_path)
    first = build_pointcloud(data, assets(), obs, store, automatic=False)
    second = build_pointcloud(data, assets(), obs, store, automatic=False)
    assert 100_000 < len(first["vertices"]) <= 150_000
    assert first["components"][0]["point_count"] > 0
    assert np.array_equal(first["vertices"], second["vertices"])
    assert np.array_equal(first["indices"], second["indices"])


def test_mask_from_another_view_is_not_accepted_by_fusion(tmp_path):
    store = Store(tmp_path)
    store.add_asset({**assets()[1], "sha256": "another-photo"})
    ref = "b" * 32
    store.add_refinement({"id": ref, "asset_id": assets()[1]["id"]})
    obs = {**observation("wrong-mask", 0, [0, 0, 1, 1]), "refinement_id": ref}
    with pytest.raises(ValueError, match="must belong"):
        build_pointcloud(geometry(), assets(), [obs], store)


def test_reprojection_links_same_housing_despite_small_depth_scale_error(tmp_path):
    data = geometry()
    data['points'][1] = data['points'][0] * 1.08
    data['points'][1, ..., 0] += 0.1
    data['depth'][1] = 1.08
    obs = [observation('front', 0, [0.2, 0.2, 0.8, 0.8]),
           observation('side', 1, [0.2, 0.2, 0.8, 0.8])]
    cloud = build_pointcloud(data, assets(), obs, Store(tmp_path))
    assert len(cloud['components']) == 1
    assert set(cloud['components'][0]['observation_ids']) == {'front', 'side'}


def test_reprojection_does_not_link_a_different_depth_layer(tmp_path):
    data = geometry()
    data['points'][1] = data['points'][0] * 1.8
    data['points'][1, ..., 0] += 0.1
    data['depth'][1] = 1.8
    obs = [observation('front', 0, [0.2, 0.2, 0.8, 0.8]),
           observation('other-depth', 1, [0.2, 0.2, 0.8, 0.8])]
    cloud = build_pointcloud(data, assets(), obs, Store(tmp_path))
    assert len(cloud['components']) == 2


def test_projection_ambiguity_does_not_choose_between_two_neighbor_housings(tmp_path):
    data = geometry()
    data['extrinsics'][1, 0, 3] = 0
    data['points'][1] = data['points'][0] * 1.08
    data['depth'][1] = 1.08
    obs = [observation('uncertain', 0, [0.2, 0.2, 0.8, 0.8]),
           observation('left', 1, [0.2, 0.2, 0.5, 0.8]),
           observation('right', 1, [0.5, 0.2, 0.8, 0.8])]
    cloud = build_pointcloud(data, assets(), obs, Store(tmp_path))
    assert len({o['component_id'] for o in cloud['observations']}) == 3


def test_subpixel_cable_mask_keeps_only_finite_positive_model_points(tmp_path):
    data = geometry()
    data['confidence'][0] = 100
    data['confidence'][0, :, 0] = 1
    data['confidence'][1] = 0
    data['depth'][0, 4, 0] = 0
    data['confidence'][0, 5, 0] = 0
    data['points'][0, 6, 0] = np.nan
    views = assets()
    views[0] = {**views[0], 'width': 100, 'height': 100}
    store = Store(tmp_path)
    store.add_asset({**views[0], 'sha256': 'thin-wire'})
    ref = 'c' * 32
    folder = tmp_path / 'refinements' / ref
    folder.mkdir()
    mask = np.zeros((100, 100), np.uint8)
    mask[:, 1] = 255  # nearest sampling at x=5,15,... erases this real mask
    Image.fromarray(mask).save(folder / 'binary-mask.png')
    store.add_refinement({'id': ref, 'asset_id': views[0]['id']})
    obs = {**observation('wire', 0, [0, 0, 0.02, 1], 'thin-wire'),
           'category': 'cables', 'label': 'Wire', 'refinement_id': ref}
    cloud = build_pointcloud(data, views, [obs], store, automatic=False)
    assert cloud['components'][0]['point_count'] == 7
    selected = cloud['vertices'][cloud['indices'] == 1]
    assert sorted(np.round(selected[:, 1], 3)) == pytest.approx([-0.9, -0.8, -0.7, -0.3, -0.2, -0.1, 0])
    assert np.allclose(selected[:, [0, 2]], [0, -1])


def test_thin_cable_uses_finer_voxels_than_scene_background(tmp_path):
    data = geometry()
    data['confidence'][1] = 0
    data['points'][0, 0, :3, 0] = [0, 0.001, 0.002]
    obs = {**observation('wire', 0, [0, 0, 0.3, 0.1], 'thin-wire'),
           'category': 'cables', 'label': 'Wire'}
    cloud = build_pointcloud(data, assets(), [obs], Store(tmp_path), automatic=False)
    assert cloud['components'][0]['point_count'] == 3


def test_reprojection_ignores_target_pixels_without_positive_confidence(tmp_path):
    data = geometry()
    data['points'][1] = data['points'][0] * 1.08
    data['points'][1, ..., 0] += 0.1
    data['depth'][1] = 1.08
    data['confidence'][1] = 0
    data['confidence'][1, :, 2] = 1  # some valid target samples, but insufficient projected support
    obs = [observation('front', 0, [0.2, 0.2, 0.8, 0.8]),
           observation('unsupported-target', 1, [0.2, 0.2, 0.8, 0.8])]
    cloud = build_pointcloud(data, assets(), obs, Store(tmp_path))
    assert len(cloud['components']) == 2


def test_reprojection_support_excludes_letterbox_padding(tmp_path):
    data = geometry()
    data['rects'][:] = [2, 2, 8, 8]
    data['points'][1] = data['points'][0] * 1.08
    data['points'][1, ..., 0] += 0.1
    data['depth'][1] = 1.08
    views = [{**v, 'width': 6, 'height': 6} for v in assets()]
    obs = [observation('front-edge', 0, [0, 0, 1/6, 1]),
           observation('side-edge', 1, [0, 0, 1/6, 1])]
    cloud = build_pointcloud(data, views, obs, Store(tmp_path))
    assert len(cloud['components']) == 2


def test_padding_depth_cannot_erase_low_confidence_cable_endpoints(tmp_path):
    data = geometry()
    data['rects'][:] = [2, 2, 8, 8]
    data['depth'][0] = 100
    data['depth'][0, 2:8, 2:8] = 1
    data['confidence'][0] = 100
    data['confidence'][0, 2:8, 2] = 1
    data['confidence'][1] = 0
    views = [{**v, 'width': 6, 'height': 6} for v in assets()]
    obs = {**observation('edge-wire', 0, [0, 0, 1/6, 1], 'edge-wire'),
           'category': 'cables', 'label': 'Wire'}
    cloud = build_pointcloud(data, views, [obs], Store(tmp_path), automatic=False)
    assert cloud['components'][0]['point_count'] == 6
