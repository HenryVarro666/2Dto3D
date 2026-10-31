import { Group, Mesh, BoxGeometry, MeshStandardMaterial } from "three";
import { describe, expect, it } from "vitest";
import { bindComponents, applyComponentState } from "./sceneState";

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
