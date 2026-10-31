"""Apply user edits while inheriting only server-owned, unchanged mask evidence."""


def apply_manual_components(components, previous, store):
    detections = []
    for component in components:
        submitted = component.model_dump(mode="json")
        old = previous.get(component.id)
        mask_fields = ("mask_polygon", "mask_polygons", "mask_model", "refinement_id")
        evidence = {"source": "manual", "score": None, **{key: None for key in mask_fields}}
        clear = "refinement_id" in component.model_fields_set and component.refinement_id is None
        if old and submitted["bbox"] == old["bbox"] and not clear:
            evidence.update({key: old.get(key) for key in mask_fields})
        if component.refinement_id:
            ref = store.get_refinement(component.refinement_id)
            evidence.update(
                refinement_id=ref["id"],
                mask_polygons=ref["mask_polygons"],
                mask_polygon=next(iter(ref["mask_polygons"]), None),
                mask_model=ref["model"],
            )
        if (
            old
            and not clear
            and evidence["refinement_id"] == old.get("refinement_id")
            and all(submitted[field] == old[field] for field in ("label", "category", "bbox"))
        ):
            evidence.update({field: old.get(field) for field in ("source", "score")})
        detections.append({**submitted, **evidence})
    return detections
