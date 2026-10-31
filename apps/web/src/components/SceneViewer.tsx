import { useEffect, useRef, useState } from "react";
import {
  ACESFilmicToneMapping,
  Box3,
  DirectionalLight,
  GridHelper,
  Group,
  HemisphereLight,
  Mesh,
  BufferGeometry,
  Float32BufferAttribute,
  Line,
  LineBasicMaterial,
  SphereGeometry,
  MeshBasicMaterial,
  CanvasTexture,
  Sprite,
  SpriteMaterial,
  Points,
  PerspectiveCamera,
  Raycaster,
  Scene,
  SRGBColorSpace,
  Vector2,
  Vector3,
  WebGLRenderer,
} from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { AlertCircle, LoaderCircle } from "lucide-react";
import {
  applyComponentState,
  bindComponents,
  componentIdFromObject,
} from "../core/sceneState";
import type { ComponentBindings } from "../core/sceneState";
import { useI18n } from "../i18n";
import type { PickedPoint } from "../api/types";
import {
  pointFromHit,
  rememberMeasurementTransforms,
} from "../core/measurement";

type Props = {
  sceneUrl: string;
  componentIds: string[];
  selectedId: string | null;
  hiddenIds: Set<string>;
  explosion: number;
  wireframe: boolean;
  resetKey: number;
  onSelect: (id: string) => void;
  onReady: () => void;
  onError?: (error: string) => void;
  pointSize?: number;
  pickPoints?: boolean;
  measurementPoints?: PickedPoint[];
  onPickPoint?: (point: PickedPoint) => void;
};

export function SceneViewer(props: Props) {
  const { t, localize } = useI18n();
  const hostRef = useRef<HTMLDivElement>(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const bindingsRef = useRef<ComponentBindings>(new Map());
  const measurementRef = useRef<
    ((points: PickedPoint[], visible: boolean) => void) | null
  >(null);
  const resetRef = useRef<(() => void) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const idsKey = props.componentIds.join("|");

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let disposed = false;
    let frame = 0;
    let root: Group | null = null;
    let renderer: WebGLRenderer;
    setError(null);
    setLoading(true);
    function fail(message: string) {
      if (!disposed) {
        setError(message);
        setLoading(false);
        propsRef.current.onError?.(message);
      }
    }
    if (!window.WebGLRenderingContext && !window.WebGL2RenderingContext) {
      fail(
        "此浏览器无法使用 WebGL。请开启浏览器硬件加速，或使用支持 WebGL 的浏览器。",
      );
      return;
    }
    try {
      renderer = new WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      fail("WebGL 初始化失败。请开启浏览器硬件加速后重新打开页面。");
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = SRGBColorSpace;
    renderer.toneMapping = ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    renderer.domElement.setAttribute("aria-label", "可旋转的三维结构示意");
    renderer.domElement.setAttribute("role", "img");
    host.appendChild(renderer.domElement);
    const scene = new Scene();
    const camera = new PerspectiveCamera(36, 1, 0.01, 1000);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = true;
    scene.add(new HemisphereLight(0xffffff, 0x8c9890, 2.5));
    const key = new DirectionalLight(0xffffff, 3.1);
    key.position.set(4, 6, 5);
    scene.add(key);
    const fill = new DirectionalLight(0xd4e9e4, 1.6);
    fill.position.set(-4, 2, -3);
    scene.add(fill);
    const floor = new GridHelper(12, 30, 0xd4dbd5, 0xe5eae5);
    scene.add(floor);
    camera.position.set(3, 2, 4);
    controls.update();
    const resize = () => {
      const width = Math.max(host.clientWidth, 1);
      const height = Math.max(host.clientHeight, 1);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();
    const animate = () => {
      if (disposed) return;
      frame = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();
    const raycaster = new Raycaster();
    const pointer = new Vector2();
    let pointerDown = { x: 0, y: 0 };
    const onDown = (event: PointerEvent) => {
      pointerDown = { x: event.clientX, y: event.clientY };
    };
    const onUp = (event: PointerEvent) => {
      if (
        event.button !== 0 ||
        Math.hypot(
          event.clientX - pointerDown.x,
          event.clientY - pointerDown.y,
        ) > 5 ||
        !root
      )
        return;
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        (-(event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(pointer, camera);
      const ids = new Set(propsRef.current.componentIds);
      for (const hit of raycaster.intersectObject(root, true)) {
        const id = componentIdFromObject(hit.object, ids);
        if (id && !propsRef.current.hiddenIds.has(id)) {
          if (propsRef.current.pickPoints) {
            if (propsRef.current.explosion !== 0) return;
            const point = pointFromHit(hit.object, hit.index, id);
            if (point) propsRef.current.onPickPoint?.(point);
          } else propsRef.current.onSelect(id);
          break;
        }
      }
    };
    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);
    new GLTFLoader().load(
      props.sceneUrl,
      (gltf) => {
        if (disposed) {
          disposeObject(gltf.scene);
          return;
        }
        root = gltf.scene;
        const bounds = new Box3().setFromObject(root);
        if (bounds.isEmpty()) {
          fail("结构文件没有可显示的几何体，请重新生成。");
          return;
        }
        bindingsRef.current = bindComponents(
          root,
          propsRef.current.componentIds,
        );
        if (!bindingsRef.current.size) {
          fail("结构文件缺少组件标识，请重新生成。");
          return;
        }
        rememberMeasurementTransforms(root);
        const center = bounds.getCenter(new Vector3());
        const size = bounds.getSize(new Vector3());
        const displayGroup = new Group();
        displayGroup.add(root);
        displayGroup.position.copy(center).negate();
        scene.add(displayGroup);
        const maxSize = Math.max(size.x, size.y, size.z, 0.1);
        raycaster.params.Points.threshold = maxSize * 0.006;
        floor.position.y = -size.y / 2 - maxSize * 0.015;
        floor.scale.setScalar(maxSize / 3);
        const markerGroup = new Group();
        displayGroup.add(markerGroup);
        measurementRef.current = (points, visible) => {
          disposeObject(markerGroup);
          markerGroup.clear();
          markerGroup.visible = visible;
          if (!visible) return;
          for (const [i, point] of points.entries()) {
            const color = i === 0 ? "#ffb547" : "#18c5ac";
            const dot = new Mesh(
              new SphereGeometry(maxSize * 0.009, 12, 10),
              new MeshBasicMaterial({ color, depthTest: false }),
            );
            dot.position.fromArray(point.position);
            dot.renderOrder = 100;
            markerGroup.add(dot);
            const label = document.createElement("canvas");
            label.width = 64;
            label.height = 64;
            const context = label.getContext("2d");
            if (context) {
              context.fillStyle = "#102d31";
              context.beginPath();
              context.arc(32, 32, 28, 0, Math.PI * 2);
              context.fill();
              context.fillStyle = color;
              context.font = "bold 38px sans-serif";
              context.textAlign = "center";
              context.textBaseline = "middle";
              context.fillText(i === 0 ? "A" : "B", 32, 33);
              const sprite = new Sprite(
                new SpriteMaterial({
                  map: new CanvasTexture(label),
                  depthTest: false,
                }),
              );
              sprite.position
                .fromArray(point.position)
                .add(new Vector3(0, maxSize * 0.035, 0));
              sprite.scale.setScalar(maxSize * 0.05);
              sprite.renderOrder = 101;
              markerGroup.add(sprite);
            }
          }
          if (points.length === 2) {
            const geometry = new BufferGeometry();
            geometry.setAttribute(
              "position",
              new Float32BufferAttribute(
                points.flatMap((p) => p.position),
                3,
              ),
            );
            const line = new Line(
              geometry,
              new LineBasicMaterial({ color: "#164b51", depthTest: false }),
            );
            line.renderOrder = 99;
            markerGroup.add(line);
          }
        };
        const reset = () => {
          const fitHeight =
            maxSize / (2 * Math.tan((camera.fov * Math.PI) / 360));
          const distance = fitHeight * Math.max(1, 1 / camera.aspect) * 1.6;
          camera.position.set(
            distance * 0.64,
            distance * 0.38,
            distance * 0.85,
          );
          camera.near = maxSize / 100;
          camera.far = maxSize * 100;
          camera.updateProjectionMatrix();
          controls.target.set(0, 0, 0);
          controls.minDistance = maxSize * 0.25;
          controls.maxDistance = maxSize * 12;
          controls.update();
        };
        resetRef.current = reset;
        reset();
        const current = propsRef.current;
        applyComponentState(
          bindingsRef.current,
          current.hiddenIds,
          current.selectedId,
          current.explosion,
          current.wireframe,
          current.pointSize,
        );
        measurementRef.current(
          current.measurementPoints ?? [],
          current.explosion === 0,
        );
        renderer.render(scene, camera);
        setLoading(false);
        current.onReady();
      },
      undefined,
      () => fail("三维结构加载失败，请检查本地服务，或重新生成结构。"),
    );
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener("pointerdown", onDown);
      renderer.domElement.removeEventListener("pointerup", onUp);
      disposeObject(scene);
      renderer.dispose();
      renderer.domElement.remove();
      bindingsRef.current.clear();
      resetRef.current = null;
      measurementRef.current = null;
    };
  }, [props.sceneUrl, idsKey]);

  // Localize the existing canvas without recreating the renderer or resetting its camera.
  useEffect(() => {
    hostRef.current
      ?.querySelector("canvas")
      ?.setAttribute("aria-label", t("可旋转的三维结构示意"));
  }, [t, props.sceneUrl, idsKey]);

  useEffect(() => {
    applyComponentState(
      bindingsRef.current,
      props.hiddenIds,
      props.selectedId,
      props.explosion,
      props.wireframe,
      props.pointSize,
    );
  }, [
    props.hiddenIds,
    props.selectedId,
    props.explosion,
    props.wireframe,
    props.pointSize,
  ]);
  useEffect(() => {
    measurementRef.current?.(
      props.measurementPoints ?? [],
      props.explosion === 0,
    );
  }, [props.measurementPoints, props.explosion]);
  useEffect(() => {
    resetRef.current?.();
  }, [props.resetKey]);
  return (
    <div className="scene-viewer">
      <div
        ref={hostRef}
        className={`canvas-host ${props.pickPoints ? "measurement-picking" : ""}`}
      />
      {loading && (
        <div className="viewer-loading">
          <LoaderCircle size={24} className="spin" />
          <span>{t("正在载入组件结构…")}</span>
        </div>
      )}
      {error && (
        <div className="viewer-error" role="alert">
          <AlertCircle size={27} />
          <strong>{t("三维视图暂不可用")}</strong>
          <p>{localize(error)}</p>
          <span>{t("组件列表、照片框选和文件导出仍可使用。")}</span>
        </div>
      )}
      <div className="axis-indicator" aria-hidden="true">
        <span className="axis-y">Y</span>
        <span className="axis-x">X</span>
        <span className="axis-z">Z</span>
        <i />
      </div>
    </div>
  );
}

function disposeObject(object: Group | Scene) {
  object.traverse((child) => {
    if (
      child instanceof Mesh ||
      child instanceof Points ||
      child instanceof Line ||
      child instanceof Sprite
    ) {
      if (!(child instanceof Sprite)) child.geometry.dispose();
      const materials = Array.isArray(child.material)
        ? child.material
        : [child.material];
      for (const material of materials) {
        if (material instanceof SpriteMaterial) material.map?.dispose();
        material.dispose();
      }
    }
  });
}
