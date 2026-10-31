import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Download, Layers3, RotateCcw, Upload, X } from "lucide-react";
import type {
  BBox,
  EditableComponent,
  ViewObservation,
  WorkbenchApi,
} from "../api/types";
import { useMultiview } from "../core/multiview";
import { useAnnotation } from "../core/annotation";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/messages";
import { PhotoPanel } from "./PhotoPanel";
import { AnnotationPanel } from "./AnnotationPanel";
import { ComponentList } from "./ComponentList";

const SceneViewer = lazy(() =>
  import("./SceneViewer").then((m) => ({ default: m.SceneViewer })),
);
const CONTEXT = "__context__";
const stageKeys: Record<string, MessageKey> = {
  queued: "等待共享队列",
  starting: "准备多图任务",
  loading_geometry_model: "载入多视角模型",
  estimating_geometry: "联合估计相机与深度",
  unprojecting: "生成共同坐标点云",
  recognizing_view: "逐图识别组件",
  manual_components: "应用组件校正",
  fusing: "融合点云与组件",
  exporting: "导出点云",
  complete: "载入视图",
};
const stages = [
  "上传照片组",
  "联合几何推理",
  "逐图识别组件",
  "融合点云与组件",
  "导出点云",
  "载入视图",
] as const;

export function MultiviewWorkbench({
  apiClient,
  onBusyChange,
}: {
  apiClient: WorkbenchApi;
  onBusyChange: (busy: boolean) => void;
}) {
  const { t, localize, componentLabel, locale } = useI18n();
  const flow = useMultiview(apiClient);
  const { state } = flow;
  const annotation = useAnnotation(apiClient);
  const input = useRef<HTMLInputElement>(null);
  const seed = useRef<ViewObservation | null>(null);
  const [previews, setPreviews] = useState<string[]>([]);
  const [view, setView] = useState(0);
  const [observations, setObservations] = useState<ViewObservation[]>([]);
  const [selectedObservation, setSelectedObservation] = useState<string | null>(
    null,
  );
  const [selectedPart, setSelectedPart] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [showContext, setShowContext] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const [pointSize, setPointSize] = useState(2);
  const [explosion, setExplosion] = useState(0);
  const [resetKey, setResetKey] = useState(0);
  const [viewerError, setViewerError] = useState<string | null>(null);
  const active = ["uploading", "processing", "preparing"].includes(state.phase);
  const locked = active || Boolean(annotation.draft) || drawing;
  useEffect(() => {
    onBusyChange(locked);
  }, [locked, onBusyChange]);
  useEffect(() => {
    const urls = state.files.map((file) =>
      typeof URL.createObjectURL === "function"
        ? URL.createObjectURL(file)
        : "",
    );
    setPreviews(urls);
    setView(0);
    setObservations([]);
    setSelectedPart(null);
    setSelectedObservation(null);
    setDirty(false);
    setHidden(new Set());
    setExplosion(0);
    setViewerError(null);
    return () => {
      urls.forEach((url) => {
        if (url) URL.revokeObjectURL(url);
      });
    };
  }, [state.files]);
  useEffect(() => {
    if (!state.result) return;
    setObservations((previous) =>
      state.result!.observations.map((o) => {
        const old = previous.find((p) => p.id === o.id);
        return {
          ...o,
          refinement_id: o.refinement_id ?? undefined,
          labelEdited:
            old?.label === o.label
              ? (old.labelEdited ?? old.source !== "grounding_dino")
              : o.source !== "grounding_dino",
        };
      }),
    );
    setDirty(false);
    setHidden(new Set());
    setExplosion(0);
  }, [state.result]);
  const asset = state.capture?.assets[view] ?? null;
  const currentObservations = observations.filter(
    (o) => o.asset_id === asset?.id,
  );
  const parts = useMemo(() => {
    const groups = new Map<string, ViewObservation[]>();
    for (const o of observations)
      groups.set(o.component_id, [...(groups.get(o.component_id) || []), o]);
    return [...groups].map(([id, group]) => ({
      ...group[0],
      id,
      observation_ids: group.map((o) => o.id),
      point_count:
        state.result?.components.find((p) => p.id === id)?.point_count ?? 0,
    }));
  }, [observations, state.result]);
  const sceneIds = useMemo(
    () => [...(state.result?.components.map((p) => p.id) ?? []), CONTEXT],
    [state.result],
  );
  const viewerHidden = useMemo(
    () => new Set([...hidden, ...(showContext ? [] : [CONTEXT])]),
    [hidden, showContext],
  );
  const hiddenObservations = new Set(
    observations.filter((o) => hidden.has(o.component_id)).map((o) => o.id),
  );
  const editable =
    Boolean(asset && state.result) && !active && !annotation.draft;
  const selected = observations.find(
    (o) => o.id === selectedObservation && o.asset_id === asset?.id,
  );

  function choose(files: File[]) {
    if (locked) return;
    annotation.cancel();
    seed.current = null;
    setDrawing(false);
    flow.selectFiles(files);
  }
  function selectObservation(id: string) {
    const o = observations.find((item) => item.id === id);
    if (!o || annotation.draft || drawing) return;
    setSelectedObservation(id);
    setSelectedPart(o.component_id);
  }
  function selectPart(id: string) {
    if (id === CONTEXT || annotation.draft || drawing) return;
    setSelectedPart(id);
    const observation =
      currentObservations.find((o) => o.component_id === id) ??
      observations.find((o) => o.component_id === id);
    if (observation) {
      const index =
        state.capture?.assets.findIndex((a) => a.id === observation.asset_id) ??
        -1;
      if (index >= 0) setView(index);
      setSelectedObservation(observation.id);
    }
  }
  function change(id: string, patch: Partial<EditableComponent>) {
    if (!editable) return;
    const old = observations.find((o) => o.id === id);
    setObservations((all) =>
      all.map((o) =>
        o.id === id ||
        (o.component_id === old?.component_id &&
          (patch.label !== undefined || patch.category !== undefined))
          ? {
              ...o,
              ...patch,
              ...(patch.label !== undefined ? { labelEdited: true } : {}),
            }
          : o,
      ),
    );
    setDirty(true);
  }
  function addBox(box: BBox) {
    if (!editable || !asset) return;
    const item = seed.current ?? {
      id: `obs-${crypto.randomUUID()}`,
      asset_id: asset.id,
      component_id: `part-${crypto.randomUUID()}`,
      category: "unknown",
      label: t("新组件 {count}", { count: parts.length + 1 }),
      bbox: box,
      source: "manual",
      score: null,
      labelEdited: true,
    };
    seed.current = item;
    setDrawing(false);
    annotation.start(asset, box, item);
  }
  function confirm(boxOnly: boolean) {
    const component = annotation.confirm(boxOnly);
    const original = seed.current;
    if (!component || !original) return;
    const next = {
      ...component,
      asset_id: original.asset_id,
      component_id: original.component_id,
    };
    setObservations((all) => {
      const remaining = all
        .filter((o) => o.id !== next.id)
        .map((o) =>
          o.component_id === next.component_id
            ? {
                ...o,
                label: next.label,
                category: next.category,
                labelEdited: next.labelEdited,
              }
            : o,
        );
      return [...remaining, next];
    });
    setSelectedObservation(next.id);
    setSelectedPart(next.component_id);
    setDirty(true);
    seed.current = null;
  }
  function associate(partId: string) {
    if (!editable || !selected) return;
    const target = parts.find((p) => p.id === partId);
    setObservations((all) =>
      all.map((o) =>
        o.id === selected.id
          ? {
              ...o,
              component_id: partId,
              ...(target
                ? {
                    label: target.label,
                    category: target.category,
                    labelEdited: target.labelEdited,
                  }
                : {}),
            }
          : o,
      ),
    );
    setSelectedPart(partId);
    setDirty(true);
  }
  function toggle(id: string) {
    setHidden((h) => {
      const next = new Set(h);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }
  const phaseStage =
    state.phase === "uploading"
      ? t("上传照片组")
      : state.phase === "preparing"
        ? t("载入视图")
        : state.phase === "idle"
          ? t("等待照片组")
          : t(stageKeys[state.job?.stage ?? "queued"] ?? "准备多图任务");
  const complete = ["ready", "review"].includes(state.phase);
  const stepIndex =
    state.phase === "uploading" || state.phase === "idle"
      ? 0
      : complete
        ? 6
        : state.phase === "preparing"
          ? 5
          : ({
              recognizing_view: 2,
              fusing: 3,
              exporting: 4,
              complete: 5,
              manual_components: 3,
            }[state.job?.stage ?? ""] ?? 1);
  const actualStages = state.mode === "manual" ? stages.slice(3) : stages;
  const progress =
    state.mode === "manual" ? Math.max(0, stepIndex - 3) : stepIndex;
  return (
    <main className="main-content multiview-workspace">
      <div className="workspace-heading">
        <div>
          <div className="breadcrumb">V3 · {t("多角度点云")}</div>
          <h1>{t("同一设备，多角度观察")}</h1>
          <p>{t("上传 2–8 张有重叠的照片，融合可见表面并关联组件。")}</p>
        </div>
        <div className="workspace-actions">
          <button
            className="button secondary"
            disabled={locked}
            onClick={() => input.current?.click()}
          >
            <Upload size={16} />
            {t("选择照片组")}
          </button>
          <button
            className="button primary"
            disabled={locked || state.files.length < 2}
            onClick={() => {
              setViewerError(null);
              void flow.start();
            }}
          >
            {t("融合并识别组件")}
          </button>
        </div>
      </div>
      <input
        className="visually-hidden"
        ref={input}
        aria-label={t("选择多角度照片")}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        disabled={locked}
        onChange={(e) => {
          choose(Array.from(e.currentTarget.files ?? []));
          e.currentTarget.value = "";
        }}
      />
      <div className="capture-guide">
        <Layers3 size={20} />
        <p>
          {t(
            "围绕静止设备拍摄：正面、左斜、右斜；保持同一焦距，让线缆和背部支架在至少两张照片中出现。",
          )}
        </p>
        <span>{t("相对尺度 · 可见表面 · 需人工核对")}</span>
      </div>
      {state.files.length > 0 && (
        <div className="photo-strip" aria-label={t("照片组")}>
          {state.files.map((file, i) => (
            <div
              className={`photo-thumb ${view === i ? "selected" : ""}`}
              key={`${i}-${file.name}`}
            >
              <button
                disabled={locked}
                aria-label={t("照片 {count}：{name}", {
                  count: i + 1,
                  name: file.name,
                })}
                aria-pressed={view === i}
                onClick={() => {
                  setView(i);
                  setSelectedObservation(null);
                  setDrawing(false);
                }}
              >
                {previews[i] && <img src={previews[i]} alt="" />}
                <span>
                  {String(i + 1).padStart(2, "0")} · {file.name}
                </span>
              </button>
              {!state.capture && (
                <button
                  className="thumb-remove"
                  disabled={locked}
                  aria-label={t("移除照片 {count}", { count: i + 1 })}
                  onClick={() => flow.removeFile(i)}
                >
                  <X size={13} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      <section
        className="task-progress multi-progress"
        aria-label={t("多图任务进度")}
      >
        <div className="task-progress-heading">
          <strong aria-live="polite">
            {complete
              ? t(state.phase === "review" ? "点云待核对" : "点云已就绪")
              : phaseStage}
            {active && state.phase === "uploading"
              ? ` · ${state.uploadIndex}/${state.files.length}`
              : active && state.job?.view_index
                ? ` · ${state.job.view_index}/${state.job.total_views}`
                : ""}
          </strong>
          <span>
            {(flow.elapsedMs / 1000).toFixed(1)} s · {t("按处理阶段更新")}
          </span>
        </div>
        <div
          className="task-progress-track"
          role="progressbar"
          aria-label={t("多图阶段进度")}
          aria-valuemin={0}
          aria-valuemax={actualStages.length}
          aria-valuenow={progress}
          aria-valuetext={phaseStage}
          aria-busy={active}
          style={{
            gridTemplateColumns: `repeat(${actualStages.length}, minmax(0, 1fr))`,
          }}
        >
          {actualStages.map((s, i) => (
            <span
              key={s}
              className={
                i < progress
                  ? "complete"
                  : i === progress && active
                    ? "current"
                    : "pending"
              }
            />
          ))}
        </div>
        <div className="multi-stage-labels">
          {actualStages.map((s) => (
            <span key={s}>{t(s)}</span>
          ))}
        </div>
        {state.mode === "manual" && (
          <p>{t("复用已生成的几何，仅更新组件归属。")}</p>
        )}
        {active && (
          <button className="text-button" onClick={flow.cancel}>
            {t("停止等待")}
          </button>
        )}
        {state.phase === "cancelled" && (
          <p>{t("已停止等待；服务端任务可能仍在完成。")}</p>
        )}
        {state.error && <p role="alert">{localize(state.error)}</p>}
      </section>
      <div className="workbench-grid">
        <PhotoPanel
          idPrefix="multi-"
          imageUrl={asset?.image_url ?? previews[view] ?? null}
          fileName={state.files[view]?.name ?? null}
          asset={asset}
          components={currentObservations}
          selectedId={selectedObservation}
          hiddenIds={hiddenObservations}
          drawing={drawing && editable}
          canDraw={editable}
          onSelect={selectObservation}
          onChoose={() => {
            if (!locked) input.current?.click();
          }}
          onFile={(file) => choose([...state.files, file])}
          onDrawingChange={(value) => {
            seed.current = null;
            setDrawing(value && editable);
          }}
          onBox={addBox}
          annotation={annotation}
        />
        <div className="model-side">
          <AnnotationPanel
            annotation={annotation}
            onConfirm={confirm}
            onRedraw={() => {
              annotation.cancel();
              setDrawing(true);
            }}
          />
          <section
            className="view-panel model-panel"
            hidden={Boolean(annotation.draft)}
            aria-labelledby="multi-model-title"
          >
            <header className="panel-heading">
              <div>
                <span className="panel-index">02</span>
                <h2 id="multi-model-title">{t("融合点云")}</h2>
              </div>
              <span className="schematic-badge">{t("尺寸未标定")}</span>
            </header>
            <div className="model-stage">
              {state.result?.scene_url ? (
                <Suspense
                  fallback={
                    <div className="viewer-loading">
                      {t("正在准备三维查看器…")}
                    </div>
                  }
                >
                  <SceneViewer
                    sceneUrl={state.result.scene_url}
                    componentIds={sceneIds}
                    selectedId={selectedPart}
                    hiddenIds={viewerHidden}
                    explosion={explosion}
                    wireframe={false}
                    resetKey={resetKey}
                    pointSize={pointSize}
                    onSelect={selectPart}
                    onReady={flow.viewerReady}
                    onError={(message) => {
                      setViewerError(message);
                      flow.viewerReady();
                    }}
                  />
                </Suspense>
              ) : (
                <div className="model-empty">
                  <Layers3 size={58} strokeWidth={1} />
                  <h3>{t("共同坐标中的彩色点云")}</h3>
                  <p>{t("选择照片组后，点击“融合并识别组件”开始。")}</p>
                </div>
              )}
            </div>
            <div className="model-toolbar multi-model-toolbar">
              <button
                className="text-button"
                onClick={() => {
                  setHidden(new Set());
                  setShowContext(true);
                  setExplosion(0);
                  setResetKey((n) => n + 1);
                }}
              >
                <RotateCcw size={14} />
                {t("恢复视图")}
              </button>
              <label>
                <input
                  type="checkbox"
                  checked={showContext}
                  onChange={(e) => setShowContext(e.target.checked)}
                />
                {t("显示背景点")}
              </label>
              <label>
                {t("点大小")}
                <input
                  aria-label={t("点大小")}
                  type="range"
                  min="1"
                  max="6"
                  step="0.5"
                  value={pointSize}
                  onChange={(e) => setPointSize(Number(e.target.value))}
                />
              </label>
              <label>
                {t("组件分解")}
                <input
                  aria-label={t("组件分解程度")}
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={explosion}
                  onChange={(e) => setExplosion(Number(e.target.value))}
                />
              </label>
            </div>
            <footer className="model-caption">
              {t("拖动旋转 · 右键平移 · 滚轮缩放")}
            </footer>
          </section>
        </div>
      </div>
      <div className="details-grid">
        <section className="components-panel" aria-label={t("当前照片的组件")}>
          <header className="components-heading">
            <div>
              <h2>{t("当前照片的组件")}</h2>
              <span className="count-badge">{currentObservations.length}</span>
              {dirty && <span className="dirty-badge">{t("校正待生成")}</span>}
            </div>
            <button
              className="button primary small"
              disabled={!editable || observations.some((o) => !o.label.trim())}
              onClick={() => {
                setDrawing(false);
                setViewerError(null);
                void flow.rebuild(observations);
              }}
            >
              {t("应用校正到点云")}
            </button>
          </header>
          <ComponentList
            components={currentObservations}
            selectedId={selectedObservation}
            hiddenIds={hiddenObservations}
            mutationsDisabled={!editable}
            onSelect={selectObservation}
            onToggle={(id) => {
              const o = observations.find((v) => v.id === id);
              if (o) toggle(o.component_id);
            }}
            onIsolate={(id) => {
              const o = observations.find((v) => v.id === id);
              if (o) {
                selectPart(o.component_id);
                setHidden(
                  new Set(
                    parts
                      .filter((p) => p.id !== o.component_id)
                      .map((p) => p.id),
                  ),
                );
                setShowContext(false);
              }
            }}
            onChange={change}
            onRemove={(id) => {
              if (editable) {
                setObservations((all) => all.filter((o) => o.id !== id));
                setDirty(true);
              }
            }}
            onRefine={(id) => {
              const o = currentObservations.find((v) => v.id === id);
              if (editable && o && asset) {
                seed.current = o;
                annotation.start(asset, o.bbox, o);
              }
            }}
          />
          {selected && (
            <div className="association-editor">
              <label>
                {t("关联到全局组件")}
                <select
                  aria-label={t("关联到全局组件")}
                  disabled={!editable}
                  value={selected.component_id}
                  onChange={(e) => associate(e.target.value)}
                >
                  {parts.map((p, i) => (
                    <option key={p.id} value={p.id}>
                      {String(i + 1).padStart(2, "0")} · {componentLabel(p)}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="text-button"
                disabled={!editable}
                onClick={() => associate(`part-${crypto.randomUUID()}`)}
              >
                {t("独立为新组件")}
              </button>
              <p>
                {t("同一物体在不同照片中的标注可关联；相邻物体请保持独立。")}
              </p>
            </div>
          )}
        </section>
        <section
          className="result-panel multi-summary"
          aria-label={t("全局组件")}
        >
          <header>
            <h2>{t("全局组件")}</h2>
            <span>
              {t("{count} 个点", {
                count: (state.result?.point_count ?? 0).toLocaleString(locale),
              })}
            </span>
          </header>
          {parts.map((p, i) => (
            <div
              key={p.id}
              className={`global-part ${selectedPart === p.id ? "selected" : ""}`}
            >
              <input
                type="checkbox"
                aria-label={t("显示全局组件 {name}", {
                  name: componentLabel(p),
                })}
                checked={!hidden.has(p.id)}
                onChange={() => toggle(p.id)}
              />
              <button
                aria-pressed={selectedPart === p.id}
                onClick={() => selectPart(p.id)}
              >
                <strong>
                  {String(i + 1).padStart(2, "0")} · {componentLabel(p)}
                </strong>
                <small>
                  {t("{views} 处标注 · {count} 个点", {
                    views: p.observation_ids.length,
                    count: p.point_count.toLocaleString(locale),
                  })}
                </small>
              </button>
            </div>
          ))}
          {!parts.length && (
            <p>{t("未识别到组件时，仍可在照片中框选补充。")}</p>
          )}
          {viewerError && <p role="alert">{localize(viewerError)}</p>}
          <p>
            {t(
              "点云呈现照片中的可见表面；遮挡处和细线可能缺失，真实尺寸未知。",
            )}
          </p>
          {state.result?.warnings.map((warning) => (
            <p className="quality-warning" key={warning}>
              {localize(warning)}
            </p>
          ))}
          {state.result && (
            <div className="export-links">
              {state.result.scene_url && (
                <a href={state.result.scene_url} download>
                  <Download size={14} />
                  GLB
                </a>
              )}
              {state.result.ply_url && (
                <a href={state.result.ply_url} download>
                  <Download size={14} />
                  PLY
                </a>
              )}
              <a href={state.result.json_url} download>
                <Download size={14} />
                JSON
              </a>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
