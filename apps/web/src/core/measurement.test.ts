import {
  Group,
  Matrix4,
  Points,
  BufferGeometry,
  Float32BufferAttribute,
  PointsMaterial,
} from "three";
import { expect, it } from "vitest";
import { pointFromHit, rememberMeasurementTransforms } from "./measurement";

it("picks the actual indexed vertex and original GLB transform, excluding centering and explosion", () => {
  const root = new Group();
  const geometry = new BufferGeometry();
  geometry.setAttribute(
    "position",
    new Float32BufferAttribute([0, 0, 0, 2, 3, 4], 3),
  );
  const points = new Points(geometry, new PointsMaterial());
  points.name = "part-a";
  points.position.set(10, 20, 30);
  root.add(points);
  rememberMeasurementTransforms(root);
  const display = new Group();
  display.position.set(-100, -200, -300);
  display.add(root);
  points.position.addScalar(500); // Simulated exploded display.
  display.updateMatrixWorld(true);
  expect(pointFromHit(points, 1, "part-a")).toEqual({
    component_id: "part-a",
    point_index: 1,
    position: [12, 23, 34],
  });
  expect(pointFromHit(points, undefined, "part-a")).toBeNull();
  expect(pointFromHit(points, 8, "part-a")).toBeNull();
  // Capture original transforms in a new scene; no global mutable transform state.
  expect(points.userData.measurementMatrix).toBeInstanceOf(Matrix4);
});
