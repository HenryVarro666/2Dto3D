import {
  Box3,
  Color,
  Mesh,
  MeshStandardMaterial,
  Object3D,
  Vector3,
} from "three";

type MaterialState = {
  material: MeshStandardMaterial;
  emissive: Color;
  intensity: number;
};
export type ComponentBinding = {
  object: Object3D;
  originalPosition: Vector3;
  direction: Vector3;
  materials: MaterialState[];
};
export type ComponentBindings = Map<string, ComponentBinding>;

export function bindComponents(
  root: Object3D,
  componentIds: string[],
): ComponentBindings {
  const ids = new Set(componentIds);
  const bindings: ComponentBindings = new Map();
  root.updateWorldMatrix(true, true);
  const bounds = new Box3().setFromObject(root);
  const center = bounds.getCenter(new Vector3());
  const distance = Math.max(bounds.getSize(new Vector3()).length() * 0.2, 0.1);
  root.traverse((object) => {
    const id =
      typeof object.userData.component_id === "string"
        ? object.userData.component_id
        : object.name;
    if (!ids.has(id) || bindings.has(id)) return;
    const worldCenter = new Box3()
      .setFromObject(object)
      .getCenter(new Vector3());
    const offset = worldCenter.clone().sub(center);
    if (offset.lengthSq() < 0.00001)
      offset.set(bindings.size % 2 ? -1 : 1, 0.4, 0.5);
    offset.normalize().multiplyScalar(distance);
    const parent = object.parent;
    const direction = parent
      ? parent
          .worldToLocal(worldCenter.clone().add(offset))
          .sub(parent.worldToLocal(worldCenter.clone()))
      : offset;
    const materials: MaterialState[] = [];
    object.traverse((child) => {
      if (!(child instanceof Mesh)) return;
      const clones = (
        Array.isArray(child.material) ? child.material : [child.material]
      ).map((material) => material.clone());
      child.material = Array.isArray(child.material) ? clones : clones[0];
      for (const material of clones)
        if (material instanceof MeshStandardMaterial)
          materials.push({
            material,
            emissive: material.emissive.clone(),
            intensity: material.emissiveIntensity,
          });
    });
    bindings.set(id, {
      object,
      originalPosition: object.position.clone(),
      direction,
      materials,
    });
  });
  return bindings;
}

export function applyComponentState(
  bindings: ComponentBindings,
  hidden: Set<string>,
  selectedId: string | null,
  explosion: number,
  wireframe: boolean,
) {
  for (const [id, binding] of bindings) {
    binding.object.visible = !hidden.has(id);
    binding.object.position
      .copy(binding.originalPosition)
      .addScaledVector(binding.direction, explosion);
    for (const { material, emissive, intensity } of binding.materials) {
      material.wireframe = wireframe;
      material.emissive.copy(
        id === selectedId ? new Color("#169b86") : emissive,
      );
      material.emissiveIntensity = id === selectedId ? 0.35 : intensity;
    }
  }
}

export function componentIdFromObject(
  object: Object3D,
  ids: Set<string>,
): string | null {
  let current: Object3D | null = object;
  while (current) {
    const id =
      typeof current.userData.component_id === "string"
        ? current.userData.component_id
        : current.name;
    if (ids.has(id)) return id;
    current = current.parent;
  }
  return null;
}
