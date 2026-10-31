"""Verify component geometry survives actual GLB serialization and reload."""

import io
import json
import struct

import numpy as np
import pytest
import trimesh


def detections():
    return [
        {
            "id": "cabinet-01",
            "category": "cabinet",
            "label": "Inverter",
            "bbox": [0.25, 0.1, 0.75, 0.6],
            "score": 0.9,
            "source": "grounding_dino",
        },
        {
            "id": "support-01",
            "category": "pole",
            "label": "Pole",
            "bbox": [0.8, 0.1, 0.85, 0.9],
            "score": 0.8,
            "source": "grounding_dino",
        },
        {
            "id": "cables-01",
            "category": "cables",
            "label": "Cables",
            "bbox": [0.4, 0.6, 0.6, 0.95],
            "score": 0.7,
            "source": "grounding_dino",
        },
    ]


def test_glb_contains_independent_pickable_nodes_extras_and_original_transforms(tmp_path):
    from pv3d.geometry import build_components, export_scene

    components, warnings = build_components(detections(), image_size=(1000, 1000))
    output = tmp_path / "scene.glb"
    export_scene(components, output)
    raw = output.read_bytes()
    json_length, chunk_type = struct.unpack_from("<II", raw, 12)
    assert chunk_type == 0x4E4F534A
    gltf = json.loads(raw[20 : 20 + json_length])
    nodes = {node["name"]: node for node in gltf["nodes"] if "mesh" in node}
    assert set(nodes) == {"cabinet-01", "support-01", "cables-01"}
    for component in components:
        assert nodes[component["id"]]["extras"]["component_id"] == component["id"]
    reloaded = trimesh.load(io.BytesIO(raw), file_type="glb", force="scene")
    assert set(reloaded.graph.nodes_geometry) == {"cabinet-01", "support-01", "cables-01"}
    for component in components:
        matrix, geometry_name = reloaded.graph[component["id"]]
        np.testing.assert_allclose(matrix[:3, 3], component["position"], atol=1e-7)
        assert len(reloaded.geometry[geometry_name].faces) > 0
    assert warnings


def test_layout_uses_one_pixel_scale_y_up_and_explicit_category_priors():
    from pv3d.geometry import build_components

    components, warnings = build_components(detections(), image_size=(1000, 1000))
    cabinet, pole, cables = components
    # Cabinet height 500px sets 2 relative units; pole height 800px uses the same scale.
    assert cabinet["dimensions"][1] == pytest.approx(2.0)
    assert pole["dimensions"][1] == pytest.approx(3.2)
    assert pole["position"][0] > cabinet["position"][0]
    assert cables["position"][1] < cabinet["position"][1]
    assert [item["primitive"] for item in components] == ["box", "cylinder", "cable_bundle"]
    assert all(item["node_name"] == item["id"] for item in components)
    assert all(item.get("mask_polygon") is None for item in components)
    assert any("depth" in warning.lower() for warning in warnings)
    assert any("scale" in warning.lower() for warning in warnings)


def test_empty_detections_produce_no_arbitrary_geometry():
    from pv3d.geometry import build_components

    components, _ = build_components([], image_size=(1000, 1000))
    assert components == []


def test_oversized_unknown_background_does_not_dominate_cabinet_scene():
    from pv3d.geometry import build_components

    parts = [
        detections()[0],
        {
            "id": "sky",
            "category": "unknown",
            "label": "Background",
            "bbox": [0, 0, 1, 1],
            "score": 0.8,
            "source": "grounding_dino",
        },
    ]
    parts[0]["bbox"] = [0.4, 0.3, 0.6, 0.6]
    components, warnings = build_components(parts, image_size=(1000, 1000))
    assert [item["id"] for item in components] == ["cabinet-01"]
    assert warnings


def test_component_named_world_remains_independent_and_keeps_its_transform(tmp_path):
    from pv3d.geometry import build_components, export_scene

    candidates = detections()[:2]
    candidates[0]["id"] = "cabinet"
    candidates[1]["id"] = "world"
    components, _ = build_components(candidates, image_size=(1000, 1000))
    components[0]["position"] = [1.25, 0.5, -0.2]
    components[1]["position"] = [-0.75, 1.5, 0.3]
    output = tmp_path / "world-component.glb"
    export_scene(components, output)
    raw = output.read_bytes()
    json_length = struct.unpack_from("<I", raw, 12)[0]
    gltf = json.loads(raw[20 : 20 + json_length])
    node_indices = {node["name"]: index for index, node in enumerate(gltf["nodes"])}
    mesh_indices = {node_indices["world"], node_indices["cabinet"]}
    parents = {
        index: parent
        for parent, node in enumerate(gltf["nodes"])
        for index in node.get("children", [])
        if index in mesh_indices
    }
    assert len(parents) == 2
    assert len(set(parents.values())) == 1
    assert parents[node_indices["world"]] not in mesh_indices
    for identifier in ("world", "cabinet"):
        node = gltf["nodes"][node_indices[identifier]]
        assert node["extras"]["component_id"] == identifier
        assert "mesh" in node
        assert not node.get("children")
    reloaded = trimesh.load(io.BytesIO(raw), file_type="glb", force="scene")
    assert set(reloaded.graph.nodes_geometry) == {"world", "cabinet"}
    root_index = gltf["scenes"][gltf.get("scene", 0)]["nodes"][0]
    root_name = gltf["nodes"][root_index]["name"]
    for component in components:
        # Trimesh's importer itself reserves 'world'; query the actual exported
        # scene root rather than its synthetic default frame.
        matrix, _ = reloaded.graph.get(frame_to=component["id"], frame_from=root_name)
        np.testing.assert_allclose(matrix[:3, 3], component["position"], atol=1e-7)
