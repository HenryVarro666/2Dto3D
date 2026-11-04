import { useEffect, useRef, useState } from "react";
import { newId } from "./ids";
import type {
  Asset,
  BBox,
  EditableComponent,
  Point,
  PointPrompt,
  Refinement,
  RefinementInput,
  WorkbenchApi,
} from "../api/types";

export type AnnotationDraft = {
  asset: Asset;
  box: BBox;
  component: EditableComponent;
  points: PointPrompt[];
};
type Pending = { generation: number; revision: number; input: RefinementInput };

export function useAnnotation(api: WorkbenchApi) {
  const [draft, setDraft] = useState<AnnotationDraft | null>(null);
  const [output, setOutput] = useState<Refinement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pointMode, setPointMode] = useState<0 | 1>(1);
  const [elapsedMs, setElapsedMs] = useState(0);
  const draftRef = useRef<AnnotationDraft | null>(null);
  const resultRef = useRef<Refinement | null>(null);
  const generation = useRef(0);
  const revision = useRef(0);
  const wanted = useRef<Pending | null>(null);
  const running = useRef<AbortController | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const began = useRef(0);

  function stop() {
    generation.current += 1;
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    wanted.current = null;
    running.current?.abort();
    running.current = null;
    draftRef.current = null;
    resultRef.current = null;
  }
  useEffect(() => () => stop(), []);
  useEffect(() => {
    if (!busy) return;
    const clock = setInterval(
      () => setElapsedMs(Date.now() - began.current),
      100,
    );
    return () => clearInterval(clock);
  }, [busy]);

  async function pump() {
    if (running.current || !wanted.current) return;
    const request = wanted.current;
    wanted.current = null;
    const controller = new AbortController();
    running.current = controller;
    try {
      const next = await api.refine(request.input, controller.signal);
      if (
        request.generation === generation.current &&
        request.revision === revision.current
      ) {
        resultRef.current = next;
        setOutput(next);
        setBusy(false);
        setElapsedMs(Date.now() - began.current);
      }
    } catch (failure) {
      if (
        request.generation === generation.current &&
        request.revision === revision.current &&
        !controller.signal.aborted
      ) {
        setError(
          failure instanceof Error
            ? failure.message
            : "边界细化未完成，请重试或仅用框保存。",
        );
        setBusy(false);
      }
    } finally {
      if (running.current === controller) running.current = null;
      if (wanted.current && !running.current)
        timer.current = setTimeout(() => void pump(), 250);
    }
  }

  function schedule(next: AnnotationDraft) {
    revision.current += 1;
    resultRef.current = null;
    setOutput(null);
    setError(null);
    setBusy(true);
    began.current = Date.now();
    setElapsedMs(0);
    wanted.current = {
      generation: generation.current,
      revision: revision.current,
      input: { asset_id: next.asset.id, bbox: next.box, points: next.points },
    };
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => void pump(), 250);
  }
  function replace(next: AnnotationDraft) {
    draftRef.current = next;
    setDraft(next);
    schedule(next);
  }
  function start(asset: Asset, box: BBox, component?: EditableComponent) {
    stop();
    setError(null);
    setPointMode(1);
    replace({
      asset,
      box,
      points: [],
      component: component ?? {
        id: `manual-${newId()}`,
        category: "unknown",
        label: "",
        bbox: box,
        source: "manual",
        labelEdited: true,
      },
    });
  }
  function update(
    patch: Partial<Pick<EditableComponent, "label" | "category">>,
  ) {
    const current = draftRef.current;
    if (!current) return;
    const next = {
      ...current,
      component: {
        ...current.component,
        ...patch,
        ...(patch.label !== undefined ? { labelEdited: true } : {}),
      },
    };
    draftRef.current = next;
    setDraft(next);
  }
  function addPoint(point: Point, label: 0 | 1) {
    const current = draftRef.current;
    if (!current) return;
    if (current.points.length >= 64) {
      setError("最多添加 64 个修正点，请撤销或清空后继续。");
      return;
    }
    const [x1, y1, x2, y2] = current.box;
    if (
      label === 1 &&
      !(point[0] >= x1 && point[0] <= x2 && point[1] >= y1 && point[1] <= y2)
    ) {
      setError("保留点请点击框内物体；排除点可以点击背景。");
      return;
    }
    replace({
      ...current,
      points: [...current.points, { x: point[0], y: point[1], label }],
    });
  }
  function undo() {
    if (draftRef.current?.points.length)
      replace({
        ...draftRef.current,
        points: draftRef.current.points.slice(0, -1),
      });
  }
  function clearPoints() {
    if (draftRef.current?.points.length)
      replace({ ...draftRef.current, points: [] });
  }
  function retry() {
    if (draftRef.current) schedule(draftRef.current);
  }
  function cancel() {
    stop();
    setDraft(null);
    setOutput(null);
    setError(null);
    setBusy(false);
  }
  function confirm(useBox = false): EditableComponent | null {
    const current = draftRef.current;
    const mask = resultRef.current;
    if (!current || !current.component.label.trim() || (!useBox && !mask))
      return null;
    const component: EditableComponent = {
      ...current.component,
      label: current.component.label.trim(),
      bbox: useBox ? current.box : mask!.geometry_bbox,
      source: "manual",
      score: null,
      refinement_id: useBox ? null : mask!.id,
      mask_polygons: useBox ? null : mask!.mask_polygons,
      mask_polygon: useBox ? null : (mask!.mask_polygons[0] ?? null),
      mask_model: useBox ? null : mask!.model,
    };
    cancel();
    return component;
  }
  return {
    draft,
    output,
    error,
    busy,
    pointMode,
    setPointMode,
    elapsedMs,
    start,
    update,
    addPoint,
    undo,
    clearPoints,
    retry,
    cancel,
    confirm,
  };
}

export type AnnotationController = ReturnType<typeof useAnnotation>;
