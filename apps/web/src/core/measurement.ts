import { Matrix4, Object3D, Points, Vector3 } from "three";
import type { PickedPoint } from "../api/types";

/** Capture GLB world transforms before attaching the centered/exploded display group. */
export function rememberMeasurementTransforms(root: Object3D) {
  root.updateWorldMatrix(true, true);
  root.traverse((object) => {
    if (object instanceof Points)
      object.userData.measurementMatrix = object.matrixWorld.clone();
  });
}

export function pointFromHit(
  object: Object3D,
  index: number | undefined,
  componentId: string,
): PickedPoint | null {
  if (
    !(object instanceof Points) ||
    index === undefined ||
    !Number.isInteger(index)
  )
    return null;
  const positions = object.geometry.getAttribute("position");
  const transform = object.userData.measurementMatrix;
  if (index < 0 || index >= positions.count || !(transform instanceof Matrix4))
    return null;
  const point = new Vector3()
    .fromBufferAttribute(positions, index)
    .applyMatrix4(transform);
  if (![point.x, point.y, point.z].every(Number.isFinite)) return null;
  return {
    component_id: componentId,
    point_index: index,
    position: [point.x, point.y, point.z],
  };
}
