"""Component-aware fusion of jointly estimated geometry, with explicit relative scale."""

import hashlib
import json

import cv2
import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import binary_dilation, median_filter
from scipy.spatial import cKDTree

from .profiles import STRING_INVERTER

CONTEXT_ID = "__context__"
MAX_POINTS = 150_000


def _valid_points(data):
    valid = np.isfinite(data["points"]).all(axis=-1)
    valid &= np.isfinite(data["depth"]) & (data["depth"] > 0)
    valid &= np.isfinite(data["confidence"]) & (data["confidence"] > 0)
    thresholds = []
    for i, (left, top, right, bottom) in enumerate(data["rects"]):
        content = np.zeros(valid.shape[1:], bool)
        content[top:bottom, left:right] = True
        valid[i] &= content
        scores = data["confidence"][i][valid[i]]
        threshold = float(np.percentile(scores, 35)) if len(scores) else 0.0
        thresholds.append(threshold)
        valid[i] &= data["confidence"][i] >= threshold
    return valid, thresholds


def _mask(observation, asset, rect, shape, store):
    width, height = asset["width"], asset["height"]
    if observation.get("refinement_id"):
        identifier = observation["refinement_id"]
        ref = store.get_refinement(identifier)
        if not ref or ref["asset_id"] != asset["id"]:
            raise ValueError("Mask evidence must belong to its observation photo")
        with Image.open(store.data_dir / "refinements" / identifier / "binary-mask.png") as source:
            mask = source.convert("L")
            if mask.size != (width, height):
                raise ValueError("Mask and observation image sizes do not agree")
    else:
        values = np.zeros((height, width), np.uint8)
        rings = observation.get("mask_polygons") or [observation.get("mask_polygon")]
        polygons = [np.rint(np.asarray(r) * [width - 1, height - 1]).astype(np.int32) for r in rings if r]
        if polygons:
            cv2.fillPoly(values, polygons, 255)  # even/odd filling retains polygon holes
        else:
            x1, y1, x2, y2 = observation["bbox"]
            values[int(y1 * height):int(np.ceil(y2 * height)),
                   int(x1 * width):int(np.ceil(x2 * width))] = 255
        mask = Image.fromarray(values)
    left, top, right, bottom = rect
    result = np.zeros(shape, bool)
    # Area coverage retains a thin foreground wire between nearest sample centers.
    sampling = Image.Resampling.BOX if observation["category"] == "cables" else Image.Resampling.NEAREST
    result[top:bottom, left:right] = np.asarray(mask.resize((right - left, bottom - top), sampling)) > 0
    return result


def _projection_support(points, view, mask, geometry):
    """Require visible mask agreement and positive, consistent target depth."""
    camera = points @ geometry["extrinsics"][view, :, :3].T + geometry["extrinsics"][view, :, 3]
    projected = camera @ geometry["intrinsics"][view].T
    pixels = np.rint(projected[:, :2] / np.maximum(projected[:, 2:], 1e-8)).clip(-1e6, 1e6).astype(int)
    height, width = mask.shape
    inside = (camera[:, 2] > 0) & (pixels[:, 0] >= 0) & (pixels[:, 0] < width)
    inside &= (pixels[:, 1] >= 0) & (pixels[:, 1] < height)
    indices = np.flatnonzero(inside)
    x, y = pixels[indices].T
    hit = binary_dilation(mask, iterations=1)[y, x]
    depth = geometry["depth"][view, y, x]
    agreement = np.isfinite(depth) & (depth > 0)
    confidence = geometry["confidence"][view, y, x]
    agreement &= np.isfinite(confidence) & (confidence > 0)
    agreement &= np.isfinite(geometry["points"][view, y, x]).all(-1)
    agreement &= np.abs(camera[indices, 2] - depth) / np.maximum(depth, 1e-8) < 0.15
    return float(hit.sum() / len(points)), float((hit & agreement).sum() / len(points))


def _associate(observations, samples, scene_scale, automatic, geometry, masks, view_indices, diagnostics):
    parents = list(range(len(observations)))
    views = [{o["asset_id"]} for o in observations]

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    matches, projected_matches = [], []
    if automatic:
        for a, first in enumerate(observations):
            pa = samples[a]
            if len(pa) < 4:
                continue
            for b in range(a + 1, len(observations)):
                second, pb = observations[b], samples[b]
                if first["asset_id"] == second["asset_id"] or first["category"] != second["category"]:
                    continue
                if len(pb) < 4:
                    continue
                threshold = max(scene_scale * 0.01, np.linalg.norm(np.ptp(pa, axis=0)) * 0.03, 1e-7)
                support = min(np.mean(cKDTree(pa).query(pb)[0] < threshold),
                              np.mean(cKDTree(pb).query(pa)[0] < threshold))
                if support >= 0.25:
                    matches.append((float(support), a, b, "spatial"))
                elif first["category"] == "cabinet":
                    ab = _projection_support(pa, view_indices[second["asset_id"]], masks[b], geometry)
                    ba = _projection_support(pb, view_indices[first["asset_id"]], masks[a], geometry)
                    if min(ab[0], ba[0]) >= 0.30 and min(ab[1], ba[1]) >= 0.25:
                        projected_matches.append((min(ab[1], ba[1]), a, b, "reprojection"))
        # The fallback must be an unambiguous mutual best match for this view pair.
        for candidate in projected_matches:
            score, a, b, _ = candidate
            alternatives = [s for s, i, j, _ in matches + projected_matches
                            if (i, j) != (a, b) and (
                                (a in (i, j) and observations[j if i == a else i]["asset_id"] == observations[b]["asset_id"])
                                or (b in (i, j) and observations[j if i == b else i]["asset_id"] == observations[a]["asset_id"]))]
            if not alternatives or score - max(alternatives) >= 0.05:
                matches.append(candidate)
        for score, a, b, method in sorted(matches, reverse=True):
            ra, rb = root(a), root(b)
            if ra != rb and not (views[ra] & views[rb]):
                parents[rb] = ra
                views[ra] |= views[rb]
                diagnostics.append({"first": observations[a]["id"], "second": observations[b]["id"],
                                    "method": method, "support": score})
    groups = {}
    for i, observation in enumerate(observations):
        key = root(i) if automatic else observation.get("component_id") or observation["id"]
        groups.setdefault(key, []).append(i)
    for key, indices in groups.items():
        identifier = str(key) if not automatic and observations[indices[0]].get("component_id") else (
            "part-" + hashlib.sha256("|".join(sorted(observations[i]["id"] for i in indices)).encode()).hexdigest()[:16]
        )
        for i in indices:
            observations[i]["component_id"] = identifier
    return list(groups.values())


def _diagnostics(data, valid):
    retained = [int(v.sum()) for v in valid]
    agreements = []
    for i in range(len(valid)):
        points = data["points"][i][valid[i]]
        points = points[::max(1, len(points) // 512)][:512]
        for j in range(len(valid)):
            if i == j or not len(points):
                continue
            extr = data["extrinsics"][j]
            camera = points @ extr[:, :3].T + extr[:, 3]
            projected = camera @ data["intrinsics"][j].T
            safe_z = np.maximum(projected[:, 2], 1e-8)
            pixels = np.rint(projected[:, :2] / safe_z[:, None]).clip(-1e6, 1e6).astype(int)
            h, w = valid[j].shape
            inside = (camera[:, 2] > 0) & (pixels[:, 0] >= 0) & (pixels[:, 0] < w)
            inside &= (pixels[:, 1] >= 0) & (pixels[:, 1] < h)
            positions = np.flatnonzero(inside)
            if len(positions):
                x, y = pixels[positions].T
                positions = positions[valid[j, y, x]]
            if len(positions):
                x, y = pixels[positions].T
                target_depth = data["depth"][j, y, x]
                consistent = np.abs(camera[positions, 2] - target_depth) / np.maximum(target_depth, 1e-8) < 0.1
                agreements.append(float(consistent.sum() / len(points)))
            else:
                agreements.append(0.0)
    centers = [-e[:, :3].T @ e[:, 3] for e in data["extrinsics"]]
    baseline = max(np.linalg.norm(a - b) for a in centers for b in centers)
    depths = data["depth"][valid]
    parallax = float(baseline / max(float(np.median(depths)), 1e-8)) if len(depths) else 0.0
    agreement = float(np.mean(agreements)) if agreements else 0.0
    warnings = []
    if sum(count >= 16 for count in retained) < 2:
        warnings.append("MULTIVIEW_TOO_FEW_VALID_VIEWS")
    if parallax < 0.001:
        warnings.append("MULTIVIEW_LOW_PARALLAX")
    if agreement < 0.01:
        warnings.append("MULTIVIEW_LOW_CROSS_VIEW_SUPPORT")
    return {"retained_per_view": retained, "cross_view_support": agreement,
            "baseline_depth_ratio": parallax, "metric_scale_status": "unknown",
            "needs_review": bool(warnings)}, warnings


def _voxel_merge(vertices, colors, indices, scale, *, fine_indices=()):
    if not len(vertices):
        return vertices.astype(np.float32), colors.astype(np.uint8), indices
    voxel_size = max(scale / 400, 1e-7)
    sizes = np.where(np.isin(indices, list(fine_indices)), voxel_size / 4, voxel_size)
    keys = np.column_stack([np.rint(vertices / sizes[:, None]).astype(np.int64), indices])
    _, inverse = np.unique(keys, axis=0, return_inverse=True)
    counts = np.bincount(inverse)
    merged = np.column_stack([np.bincount(inverse, weights=v) / counts for v in vertices.T])
    rgb = np.column_stack([np.bincount(inverse, weights=v) / counts for v in colors.T])
    component_indices = np.zeros(len(counts), np.uint32)
    component_indices[inverse] = indices
    if len(merged) > MAX_POINTS:
        # At least one point per component; proportionally sample each group deterministically.
        selected = []
        for index in np.unique(component_indices):
            group = np.flatnonzero(component_indices == index)
            budget = max(1, int((MAX_POINTS - len(np.unique(component_indices))) * len(group) / len(merged)))
            selected.extend(group[np.linspace(0, len(group) - 1, min(budget, len(group)), dtype=int)])
        selected = np.asarray(selected)
        merged, rgb, component_indices = merged[selected], rgb[selected], component_indices[selected]
    return merged.astype(np.float32), np.rint(rgb).astype(np.uint8), component_indices


def build_pointcloud(geometry, assets, observations, store, automatic=True):
    observations = [dict(o) for o in observations]
    valid, thresholds = _valid_points(geometry)
    view_indices = {a["id"]: i for i, a in enumerate(assets)}
    raw_masks = [_mask(o, assets[view_indices[o["asset_id"]]], geometry["rects"][view_indices[o["asset_id"]]],
                       valid.shape[1:], store) for o in observations]
    original_valid = valid.copy()
    recovery = []
    for observation, mask in zip(observations, raw_masks):
        if observation["category"] != "cables":
            continue
        i = view_indices[observation["asset_id"]]
        depth, confidence = geometry["depth"][i], geometry["confidence"][i]
        finite = np.isfinite(geometry["points"][i]).all(-1) & np.isfinite(depth) & (depth > 0)
        finite &= np.isfinite(confidence) & (confidence > 0)
        candidates = mask & finite
        if not candidates.any():
            continue
        threshold = float(np.percentile(confidence[candidates], 20))
        local_depth = median_filter(np.where(finite, depth, 0), size=3, mode="nearest")
        consistent = (local_depth > 0) & (np.abs(depth - local_depth) / np.maximum(local_depth, 1e-8) < 0.15)
        valid[i] |= candidates & (confidence >= threshold) & consistent
        recovery.append({"observation_id": observation["id"], "confidence_threshold": threshold})
    visible = geometry["points"][valid]
    scale = float(np.linalg.norm(np.diff(np.quantile(visible, [0.01, 0.99], axis=0), axis=0))) if len(visible) else 1.0
    masks, samples = [], []
    for observation, raw_mask in zip(observations, raw_masks):
        i = view_indices[observation["asset_id"]]
        mask = raw_mask & valid[i]
        masks.append(mask)
        points = geometry["points"][i][mask]
        samples.append(points[::max(1, len(points) // 1500)][:1500])
    associations = []
    groups = _associate(observations, samples, scale, automatic, geometry, raw_masks, view_indices, associations)
    assignment = np.zeros(valid.shape, np.uint32)
    group_for = {i: g + 1 for g, group in enumerate(groups) for i in group}
    # More specific masks win; explicit manual evidence wins over automatic evidence.
    order = sorted(range(len(observations)), key=lambda i: (observations[i].get("source") == "manual", -masks[i].sum()))
    for i in order:
        assignment[view_indices[observations[i]["asset_id"]]][masks[i]] = group_for[i]
    fine_indices = [i for i, group in enumerate(groups, 1) if observations[group[0]]["category"] == "cables"]
    vertices, colors, indices = _voxel_merge(visible, geometry["colors"][valid], assignment[valid], scale,
                                            fine_indices=fine_indices)
    vertices *= [1, -1, -1]  # One OpenCV-to-Y-up transform, shared by all exported artifacts.
    components = []
    for group_index, group in enumerate(groups, 1):
        evidence = max((observations[i] for i in group),
                       key=lambda o: (o.get("source") == "manual", o.get("score") or 0))
        points = vertices[indices == group_index]
        low, high = (points.min(0), points.max(0)) if len(points) else (np.zeros(3), np.zeros(3))
        components.append({"id": evidence["component_id"], "category": evidence["category"],
                           "label": evidence["label"], "source": evidence.get("source", "manual"),
                           "score": evidence.get("score"), "observation_ids": [observations[i]["id"] for i in group],
                           "point_count": len(points), "color": STRING_INVERTER[evidence["category"]]["color"],
                           "position": ((low + high) / 2).tolist(), "dimensions": (high - low).tolist()})
    quality, warnings = _diagnostics(geometry, valid)
    quality.update(confidence_percentile=35, confidence_thresholds=thresholds, exported_points=len(vertices),
                   association_method="spatial_and_bidirectional_reprojection" if automatic else "explicit_observation_groups",
                   associations=associations, cable_confidence_percentile=20, cable_voxel_size_ratio=0.25,
                   cable_recovery=recovery,
                   cable_recovered_per_view=[int((a & ~b).sum()) for a, b in zip(valid, original_valid)])
    if automatic and components:
        warnings.append("MULTIVIEW_ASSOCIATIONS_REQUIRE_CONFIRMATION")
    if not components:
        warnings.append("MULTIVIEW_NO_COMPONENTS_ADD_MANUALLY")
        quality["needs_review"] = True
    if any(c["point_count"] == 0 for c in components):
        warnings.append("MULTIVIEW_COMPONENT_WITHOUT_POINTS")
        quality["needs_review"] = True
    return {"vertices": vertices, "colors": colors, "indices": indices,
            "context_point_count": int(np.sum(indices == 0)), "observations": observations,
            "components": components, "quality": quality, "warnings": warnings}


def export_pointcloud(cloud, folder):
    if not len(cloud["vertices"]):
        return False
    folder.mkdir(parents=True, exist_ok=True)
    mapping = {"0": CONTEXT_ID, **{str(i): c["id"] for i, c in enumerate(cloud["components"], 1)}}
    scene = trimesh.Scene(base_frame="__pv3d_scene_root__")
    for index, identifier in mapping.items():
        selected = cloud["indices"] == int(index)
        if selected.any():
            points = trimesh.points.PointCloud(cloud["vertices"][selected], cloud["colors"][selected])
            scene.add_geometry(points, node_name=identifier, geom_name=identifier)

    def metadata(tree):
        tree["asset"]["extras"] = {"representation": "fused_point_cloud", "metric_scale_status": "unknown",
                                    "coordinates": "Y-up", "component_map": mapping}
        for node in tree["nodes"]:
            if node.get("name") in mapping.values():
                node["extras"] = {"component_id": node["name"]}

    raw = trimesh.exchange.gltf.export_glb(scene, tree_postprocessor=metadata)
    (folder / "cloud.glb").write_bytes(raw)
    (folder / "component-map.json").write_text(json.dumps(mapping), encoding="utf-8")
    dtype = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
                      ("red", "u1"), ("green", "u1"), ("blue", "u1"), ("component_index", "<u4")])
    packed = np.empty(len(cloud["vertices"]), dtype=dtype)
    for key, values in zip(("x", "y", "z"), cloud["vertices"].T, strict=True):
        packed[key] = values
    for key, values in zip(("red", "green", "blue"), cloud["colors"].T, strict=True):
        packed[key] = values
    packed["component_index"] = cloud["indices"]
    header = ("ply\nformat binary_little_endian 1.0\ncomment pv3d relative scale; Y-up; "
              "component_index follows result.components order + 1; 0 = context\n"
              f"element vertex {len(packed)}\nproperty float x\nproperty float y\nproperty float z\n"
              "property uchar red\nproperty uchar green\nproperty uchar blue\nproperty uint component_index\nend_header\n")
    (folder / "cloud.ply").write_bytes(header.encode() + packed.tobytes())
    return True
