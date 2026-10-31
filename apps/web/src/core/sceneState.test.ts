import {
  Group,
  Mesh,
  BoxGeometry,
  MeshStandardMaterial,
  Points,
  PointsMaterial,
  BufferGeometry,
  Float32BufferAttribute,
} from "three";
import { describe, expect, it } from "vitest";
import { bindComponents, applyComponentState } from "./sceneState";

it("selects and hides native point groups while preserving original transforms and RGB", () => {
  const scene = new Group();
  const geometry = new BufferGeometry();
  geometry.setAttribute(
    "position",
    new Float32BufferAttribute([0, 0, 0, 1, 1, 1], 3),
  );
  const points = new Points(
    geometry,
    new PointsMaterial({ color: "#ffffff", vertexColors: true }),
  );
  points.name = "part-1";
  points.position.set(2, 1, 0);
  scene.add(points);
  const bindings = bindComponents(scene, ["part-1"]);
  applyComponentState(bindings, new Set(), "part-1", 1, false, 3);
  expect(points.material.size).toBeGreaterThan(3);
  expect(points.material.color.getHex()).not.toBe(0xffffff);
  applyComponentState(bindings, new Set(["part-1"]), null, 0, false, 2);
  expect(points.visible).toBe(false);
  expect(points.position.toArray()).toEqual([2, 1, 0]);
  expect(points.material.color.getHex()).toBe(0xffffff);
  expect(points.material.size).toBe(2);
});

describe("independent GLB component state", () => {
  it("links extras and names, hides independently, and restores exact transforms after explosion", () => {
    const scene = new Group();
    const a = new Mesh(new BoxGeometry(), new MeshStandardMaterial());
    a.name = "cabinet-1";
    a.position.set(2, 1, 0);
    const b = new Mesh(new BoxGeometry(), new MeshStandardMaterial());
    b.name = "exported-mesh";
    b.userData.component_id = "bracket-2";
    b.position.set(-2, 0, 0);
    scene.add(a, b);
    const bindings = bindComponents(scene, ["cabinet-1", "bracket-2"]);
    expect([...bindings.keys()]).toEqual(["cabinet-1", "bracket-2"]);
    applyComponentState(bindings, new Set(["bracket-2"]), "cabinet-1", 1, true);
    expect(a.visible).toBe(true);
    expect(b.visible).toBe(false);
    expect(a.position.toArray()).not.toEqual([2, 1, 0]);
    expect((a.material as MeshStandardMaterial).wireframe).toBe(true);
    applyComponentState(bindings, new Set(), null, 0, false);
    expect(a.position.toArray()).toEqual([2, 1, 0]);
    expect(b.position.toArray()).toEqual([-2, 0, 0]);
    expect(b.visible).toBe(true);
  });
});
