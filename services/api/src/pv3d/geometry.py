"""Relative, Y-up component geometry derived from image evidence and labeled priors."""

from pathlib import Path
from uuid import uuid4

import numpy as np
import trimesh

from .profiles import STRING_INVERTER
from .schemas import Detection


def build_components(detections: list[dict], image_size: tuple[int, int]) -> tuple[list[dict], list[str]]:
    """Map every bbox with one shared pixel scale; preserve available mask evidence."""
    validated = [Detection.model_validate(item).model_dump() for item in detections]
    warnings = [
        "Metric scale is unknown; all geometry uses relative display units.",
        "Depth and hidden surfaces use category priors, not recovered measurements.",
        "An exploded view explains visible component composition, not a verified disassembly procedure.",
    ]
    if not validated:
        return [], warnings + ["No usable components were recognized. Add or correct boxes manually."]

    image_width, image_height = image_size
    cabinets = [item for item in validated if item["category"] == "cabinet"]
    reference = max(cabinets or validated, key=lambda item: _area(item["bbox"]))
    ref_x1, ref_y1, ref_x2, ref_y2 = reference["bbox"]
    ref_height = (ref_y2 - ref_y1) * image_height
    pixel_scale = 2.0 / ref_height
    center_x = (ref_x1 + ref_x2) * image_width / 2
    center_y = (ref_y1 + ref_y2) * image_height / 2
    components, seen_ids = [], set()
    for item in validated:
        x1, y1, x2, y2 = item["bbox"]
        if cabinets and item["category"] == "unknown" and item["source"] != "manual":
            inside_context = ref_x1 - (ref_x2 - ref_x1) <= (x1 + x2) / 2 <= ref_x2 + (
                ref_x2 - ref_x1
            ) and ref_y1 - (ref_y2 - ref_y1) <= (y1 + y2) / 2 <= ref_y2 + (ref_y2 - ref_y1)
            if _area(item["bbox"]) > 4 * _area(reference["bbox"]) or not inside_context:
                warnings.append(
                    "An oversized or distant unknown detection was excluded from the cabinet schematic."
                )
                continue
        profile = STRING_INVERTER[item["category"]]
        width = (x2 - x1) * image_width * pixel_scale
        height = (y2 - y1) * image_height * pixel_scale
        depth = (
            width if item["category"] == "pole" else max(0.015, min(width, height) * profile["depth_ratio"])
        )
        identifier = item["id"] or f"component-{uuid4().hex[:12]}"
        if identifier in seen_ids:
            raise ValueError("Duplicate component ID")
        seen_ids.add(identifier)
        components.append(
            {
                **item,
                "id": identifier,
                "primitive": profile["primitive"],
                "color": profile["color"],
                "position": [
                    ((x1 + x2) * image_width / 2 - center_x) * pixel_scale,
                    (center_y - (y1 + y2) * image_height / 2) * pixel_scale,
                    profile["z"],
                ],
                "dimensions": [width, height, depth],
                "node_name": identifier,
            }
        )
    return components, warnings


def _area(bbox):
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])


def _vertical_cylinder(radius, height):
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=16)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    return mesh


def export_scene(components: list[dict], output: Path) -> None:
    """Write one independently pickable GLB node per stable component ID."""
    if not components:
        raise ValueError("Cannot export a scene without components")
    # Component IDs start with an alphanumeric character, so this private frame
    # cannot collide with any accepted ID (including Trimesh's default 'world').
    scene = trimesh.Scene(base_frame="__pv3d_scene_root__")
    for component in components:
        width, height, depth = component["dimensions"]
        if component["primitive"] == "cylinder":
            mesh = _vertical_cylinder(width / 2, height)
        elif component["primitive"] == "cable_bundle":
            strands = []
            radius = min(width / 8, depth / 2)
            for offset in (-width / 3, 0, width / 3):
                strand = _vertical_cylinder(radius, height)
                strand.apply_translation([offset, 0, 0])
                strands.append(strand)
            mesh = trimesh.util.concatenate(strands)
        else:
            mesh = trimesh.creation.box(extents=[width, height, depth])
        mesh.visual.face_colors = trimesh.visual.color.hex_to_rgba(component["color"])
        transform = np.eye(4)
        transform[:3, 3] = component["position"]
        scene.add_geometry(
            mesh, node_name=component["id"], geom_name=f"{component['id']}-mesh", transform=transform
        )

    def add_component_metadata(tree):
        tree.setdefault("asset", {}).setdefault("extras", {}).update(
            {
                "representation": "structural_schematic",
                "metric_scale_status": "unknown",
                "up_axis": "Y",
            }
        )
        component_ids = {component["id"] for component in components}
        for node in tree.get("nodes", []):
            if node.get("name") in component_ids:
                node.setdefault("extras", {})["component_id"] = node["name"]

    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = trimesh.exchange.gltf.export_glb(scene, tree_postprocessor=add_component_metadata)
    temporary = output.with_suffix(".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(output)
