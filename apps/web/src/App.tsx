import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Box,
  Check,
  ChevronRight,
  FileJson,
  Focus,
  Info,
  Layers3,
  RotateCcw,
  ScanLine,
  Upload,
  WandSparkles,
} from "lucide-react";
import { api } from "./api/client";
import type {
  BBox,
  EditableComponent,
  WorkbenchApi,
  SceneMode,
} from "./api/types";
import { useWorkbench } from "./core/workflow";
import { ComponentList } from "./components/ComponentList";
import { ModelHealth } from "./components/ModelHealth";
import { PhotoPanel } from "./components/PhotoPanel";
import { ProcessingStatus } from "./components/ProcessingStatus";
import { LanguageSwitcher } from "./components/LanguageSwitcher";
import { I18nProvider, useI18n } from "./i18n";
import { useAnnotation } from "./core/annotation";
import { AnnotationPanel } from "./components/AnnotationPanel";
import { DetectionScope } from "./components/DetectionScope";
import { MultiviewWorkbench } from "./components/MultiviewWorkbench";

const SceneViewer = lazy(() =>
  import("./components/SceneViewer").then((module) => ({
    default: module.SceneViewer,
  })),
);

function Workbench({ apiClient = api }: { apiClient?: WorkbenchApi }) {
  const { t, localize, componentLabel } = useI18n();
  const [captureMode, setCaptureMode] = useState<"single" | "multiview">(
    "single",
  );
  const [multiOpened, setMultiOpened] = useState(false);
  const [multiBusy, setMultiBusy] = useState(false);
  const [sceneMode, setSceneMode] = useState<SceneMode>("single");
  const { state, elapsedMs, selectPhoto, rebuild, cancel, viewerReady } =
    useWorkbench(apiClient, sceneMode);
  const annotation = useAnnotation(apiClient);
  const redrawSeed = useRef<EditableComponent | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewRef = useRef<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [components, setComponents] = useState<EditableComponent[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(new Set());
  const [drawing, setDrawing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [explosion, setExplosion] = useState(0);
  const [wireframe, setWireframe] = useState(false);
  const [resetKey, setResetKey] = useState(0);
  const [viewerError, setViewerError] = useState<string | null>(null);
  const [editRequestId, setEditRequestId] = useState<string | null>(null);
  const active = ["uploading", "processing", "preparing"].includes(state.phase);
  const assetId = state.asset?.id;
  const sceneIds = useMemo(
    () => state.result?.components.map((item) => item.id) || [],
    [state.result],
  );
  useEffect(
    () => () => {
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    },
    [],
  );
  useEffect(() => {
    setComponents([]);
    setHiddenIds(new Set());
    setSelectedId(null);
    setDirty(false);
    setExplosion(0);
  }, [assetId]);
  useEffect(() => {
    if (!state.result) return;
    const received = state.result.components;
    setComponents((current) =>
      received.map((component) => {
        const previous = current.find((item) => item.id === component.id);
        return {
          ...component,
          // Server null means no saved reference. Reserve client null for an
          // explicit box-only edit, otherwise unchanged evidence would be cleared.
          refinement_id: component.refinement_id ?? undefined,
          labelEdited:
            previous?.label === component.label
              ? (previous.labelEdited ?? previous.source !== "grounding_dino")
              : component.source !== "grounding_dino",
        };
      }),
    );
    setHiddenIds(new Set());
    setSelectedId(null);
    setDirty(false);
    setExplosion(0);
  }, [state.result]);

  function chooseFile(file: File) {
    annotation.cancel();
    redrawSeed.current = null;
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    const nextPreview =
      typeof URL.createObjectURL === "function"
        ? URL.createObjectURL(file)
        : null;
    previewRef.current = nextPreview;
    setPreview(nextPreview);
    setFileName(file.name);
    setDrawing(false);
    setComponents([]);
    setSelectedId(null);
    setHiddenIds(new Set());
    setDirty(false);
    setViewerError(null);
    void selectPhoto(file);
  }
  function changeDrawing(value: boolean) {
    redrawSeed.current = null;
    setDrawing(value && canDraw);
  }
  function addBox(bbox: BBox) {
    if (active || !state.asset) return;
    const component: EditableComponent = redrawSeed.current ?? {
      id: `manual-${crypto.randomUUID()}`,
      bbox,
      category: "unknown",
      label: t("新组件 {count}", { count: components.length + 1 }),
      source: "manual",
      score: null,
      color: "#bc9563",
      labelEdited: true,
    };
    redrawSeed.current = null;
    annotation.start(state.asset, bbox, component);
    setDrawing(false);
  }
  function confirmAnnotation(boxOnly: boolean) {
    if (active) return;
    const component = annotation.confirm(boxOnly);
    if (!component) return;
    setComponents((current) =>
      current.some((item) => item.id === component.id)
        ? current.map((item) => (item.id === component.id ? component : item))
        : [...current, component],
    );
    setSelectedId(component.id);
    setEditRequestId(component.id);
    setDirty(true);
  }
  function toggleHidden(id: string) {
    setHiddenIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function resetView() {
    setExplosion(0);
    setHiddenIds(new Set());
    setWireframe(false);
    setResetKey((current) => current + 1);
  }
  function manualRebuild() {
    if (active || annotation.draft) return;
    redrawSeed.current = null;
    setDrawing(false);
    setViewerError(null);
    void rebuild(
      components.map(({ id, category, label, bbox, refinement_id }) => ({
        id,
        category,
        label: label.trim(),
        bbox,
        ...(refinement_id !== undefined ? { refinement_id } : {}),
      })),
    );
  }
  const completedStep = state.result ? 3 : state.asset ? 2 : preview ? 1 : 0;
  const imageUrl = state.asset?.image_url || preview;
  const selected = components.find((item) => item.id === selectedId);
  const canDraw = Boolean(state.asset) && !active && !annotation.draft;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label={t("PV Structure 工作台首页")}>
          <span className="brand-mark">
            <Box size={24} strokeWidth={1.7} />
          </span>
          <span>
            PV<span className="brand-light">STRUCTURE</span>
          </span>
          <small>{t("设备结构实验室")}</small>
        </a>
        <div className="topbar-meta">
          <span className="local-badge">
            <span />
            {t("本地工作空间")}
          </span>
          <span className="topbar-divider" />
          <span className="phase-badge">{t("一期")}</span>
          <LanguageSwitcher />
        </div>
      </header>
      <nav className="capture-mode" aria-label={t("重建模式")}>
        <button
          aria-pressed={captureMode === "single"}
          disabled={active || Boolean(annotation.draft) || drawing || multiBusy}
          onClick={() => setCaptureMode("single")}
        >
          {t("单张照片")}
        </button>
        <button
          aria-pressed={captureMode === "multiview"}
          disabled={active || Boolean(annotation.draft) || drawing || multiBusy}
          onClick={() => {
            setMultiOpened(true);
            setCaptureMode("multiview");
          }}
        >
          {t("多角度点云")} <small aria-hidden="true">V3</small>
        </button>
      </nav>
      <div hidden={captureMode !== "single"}>
        <main className="main-content">
          <div className="workspace-heading">
            <div>
              <div className="breadcrumb">
                {t("工作空间")} <ChevronRight size={12} />
                <span>{t("照片 → 组件结构")}</span>
              </div>
              <h1>
                {t("设备结构工作台")}
                <span aria-hidden="true">{t("一期")}</span>
              </h1>
              <p>{t("组串式逆变器与外部安装结构的可交互示意")}</p>
            </div>
            <div className="workspace-actions">
              <ModelHealth api={apiClient} />
              <button
                className="button secondary upload-button"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={16} />
                {imageUrl ? t("更换照片") : t("导入照片")}
              </button>
            </div>
          </div>
          <input
            className="visually-hidden"
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            aria-label={t("选择设备照片")}
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) chooseFile(file);
              event.currentTarget.value = "";
            }}
          />

          <nav className="workflow-steps" aria-label={t("处理步骤")}>
            {[
              [t("导入照片"), t("单张现场照片")],
              [t("识别组件"), t("可见组件候选")],
              [t("查看结构"), t("独立组件示意")],
            ].map(([label, detail], index) => (
              <div
                key={label}
                className={`workflow-step ${completedStep > index ? "complete" : completedStep === index ? "current" : ""}`}
              >
                <span className="step-number">
                  {completedStep > index ? (
                    <Check size={14} />
                  ) : (
                    String(index + 1).padStart(2, "0")
                  )}
                </span>
                <strong>{label}</strong>
                <small>{detail}</small>
                {index < 2 && (
                  <ChevronRight className="step-chevron" size={15} />
                )}
              </div>
            ))}
            <span className="workflow-scope">
              <span className="tiny-dot" />
              {t("单图 · 相对尺度 · 可人工校正")}
            </span>
          </nav>

          <DetectionScope
            value={sceneMode}
            onChange={setSceneMode}
            disabled={active || Boolean(annotation.draft)}
            canRetry={Boolean(state.asset)}
            onRetry={() => {
              setDrawing(false);
              redrawSeed.current = null;
              setViewerError(null);
              void rebuild();
            }}
          />

          <ProcessingStatus
            state={state}
            elapsedMs={elapsedMs}
            viewerError={viewerError}
            retryDisabled={Boolean(annotation.draft)}
            onCancel={cancel}
            onRetry={() => {
              setDrawing(false);
              redrawSeed.current = null;
              setViewerError(null);
              void rebuild();
            }}
          />

          <div className="workbench-grid">
            <PhotoPanel
              imageUrl={imageUrl}
              fileName={fileName}
              asset={state.asset}
              components={components}
              selectedId={selectedId}
              hiddenIds={hiddenIds}
              drawing={drawing && canDraw}
              canDraw={canDraw}
              onSelect={setSelectedId}
              onChoose={() => fileInputRef.current?.click()}
              onFile={chooseFile}
              onDrawingChange={changeDrawing}
              onBox={addBox}
              annotation={annotation}
            />

            <div className="model-side">
              <AnnotationPanel
                annotation={annotation}
                onConfirm={confirmAnnotation}
                onRedraw={() => {
                  redrawSeed.current = annotation.draft?.component ?? null;
                  annotation.cancel();
                  setDrawing(true);
                }}
              />
              <section
                hidden={Boolean(annotation.draft)}
                className="view-panel model-panel"
                aria-labelledby="model-title"
              >
                <header className="panel-heading">
                  <div>
                    <span className="panel-index">02</span>
                    <h2 id="model-title">{t("三维结构")}</h2>
                    <span className="panel-heading-note" aria-hidden="true">
                      3D
                    </span>
                  </div>
                  <span className="schematic-badge">
                    {t("结构示意 · 比例估计")}
                  </span>
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
                        selectedId={selectedId}
                        hiddenIds={hiddenIds}
                        explosion={explosion}
                        wireframe={wireframe}
                        resetKey={resetKey}
                        onSelect={setSelectedId}
                        onReady={viewerReady}
                        onError={(error) => {
                          setViewerError(error);
                          viewerReady();
                        }}
                      />
                    </Suspense>
                  ) : (
                    <div className="model-empty">
                      <div className="model-grid" />
                      <div className="empty-model-symbol">
                        <Box size={60} strokeWidth={0.9} />
                        <span />
                        <i />
                      </div>
                      <h3>
                        {active
                          ? t("正在准备组件结构")
                          : t("在这里查看设备的组成")}
                      </h3>
                      <p>
                        {active
                          ? t("识别完成后，三维视图将自动载入")
                          : t("上传照片后，旋转、选择并逐个查看组件")}
                      </p>
                      <div className="empty-interactions">
                        <span>
                          <RotateCcw size={13} />
                          {t("旋转")}
                        </span>
                        <span>
                          <Focus size={13} />
                          {t("选中")}
                        </span>
                        <span>
                          <Layers3 size={13} />
                          {t("分解")}
                        </span>
                      </div>
                    </div>
                  )}
                  <span className="scale-badge">
                    <Info size={12} />
                    {t("尺寸未标定")}
                  </span>
                  {selected && (
                    <div className="selected-component">
                      <span
                        style={{ background: selected.color || "#719c92" }}
                      />
                      <strong>{componentLabel(selected)}</strong>
                      <button
                        className="text-button"
                        onClick={() =>
                          setHiddenIds(
                            new Set(
                              components
                                .filter((item) => item.id !== selected.id)
                                .map((item) => item.id),
                            ),
                          )
                        }
                      >
                        {t("只看此组件")} <Focus size={12} />
                      </button>
                    </div>
                  )}
                </div>
                <div className="model-toolbar">
                  <div className="view-tool-buttons">
                    <button
                      className="tool-button"
                      onClick={resetView}
                      disabled={!state.result?.scene_url}
                    >
                      <RotateCcw size={14} />
                      {t("恢复视图")}
                    </button>
                    <label className="wireframe-toggle">
                      <input
                        type="checkbox"
                        checked={wireframe}
                        disabled={!state.result?.scene_url}
                        onChange={(event) => setWireframe(event.target.checked)}
                      />
                      {t("线框")}
                    </label>
                  </div>
                  <label className="explosion-control">
                    <Layers3 size={14} />
                    <span>{t("组件分解")}</span>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={explosion}
                      disabled={!state.result?.scene_url}
                      onChange={(event) =>
                        setExplosion(Number(event.target.value))
                      }
                      aria-label={t("组件分解程度")}
                    />
                    <span className="explosion-value">
                      {Math.round(explosion * 100)}%
                    </span>
                  </label>
                </div>
                <footer className="model-caption">
                  <span>{t("拖动旋转 · 右键平移 · 滚轮缩放")}</span>
                  <span>Y ↑</span>
                </footer>
              </section>
            </div>
          </div>

          <div className="details-grid">
            <section
              className="components-panel"
              aria-labelledby="components-title"
            >
              <header className="components-heading">
                <div>
                  <span className="section-icon">
                    <Layers3 size={17} />
                  </span>
                  <h2 id="components-title">{t("组件候选")}</h2>
                  <span className="count-badge">
                    {String(components.length).padStart(2, "0")}
                  </span>
                  {dirty && (
                    <span className="dirty-badge">{t("校正待生成")}</span>
                  )}
                </div>
                <div className="component-heading-actions">
                  <button
                    className={`text-button ${drawing ? "active" : ""}`}
                    disabled={!canDraw}
                    onClick={() => changeDrawing(!drawing)}
                  >
                    <ScanLine size={14} />
                    {t("添加组件框")}
                  </button>
                  <button
                    className="button primary small"
                    disabled={
                      !canDraw ||
                      !components.length ||
                      components.some((item) => !item.label.trim())
                    }
                    onClick={manualRebuild}
                  >
                    <WandSparkles size={14} />
                    {t("重新生成结构")}
                  </button>
                </div>
              </header>
              {components.length ? (
                <ComponentList
                  components={components}
                  selectedId={selectedId}
                  hiddenIds={hiddenIds}
                  onSelect={setSelectedId}
                  onToggle={toggleHidden}
                  onIsolate={(id) => {
                    setSelectedId(id);
                    setHiddenIds(
                      new Set(
                        components
                          .filter((item) => item.id !== id)
                          .map((item) => item.id),
                      ),
                    );
                  }}
                  onChange={(id, patch) => {
                    if (active || annotation.draft) return;
                    setComponents((current) =>
                      current.map((item) =>
                        item.id === id
                          ? {
                              ...item,
                              ...patch,
                              ...(patch.label !== undefined
                                ? { labelEdited: true }
                                : {}),
                            }
                          : item,
                      ),
                    );
                    setDirty(true);
                  }}
                  onRemove={(id) => {
                    if (active || annotation.draft) return;
                    setComponents((current) =>
                      current.filter((item) => item.id !== id),
                    );
                    setDirty(true);
                    if (selectedId === id) setSelectedId(null);
                  }}
                  editRequestId={editRequestId}
                  mutationsDisabled={active || Boolean(annotation.draft)}
                  onRefine={(id) => {
                    const component = components.find((item) => item.id === id);
                    if (component && state.asset) {
                      redrawSeed.current = null;
                      setDrawing(false);
                      annotation.start(state.asset, component.bbox, component);
                    }
                  }}
                />
              ) : (
                <div className="components-empty">
                  <span>
                    <Layers3 size={25} strokeWidth={1.3} />
                  </span>
                  <div>
                    <strong>{t("还没有组件候选")}</strong>
                    <p>
                      {state.asset && !active
                        ? t("未识别到组件时，可在照片上手动框选并命名。")
                        : t("照片中的可见机柜、安装支架和线缆会列在这里。")}
                    </p>
                  </div>
                  {state.asset && !active && (
                    <button
                      className="text-button"
                      onClick={() => changeDrawing(true)}
                    >
                      {t("开始框选")} <ArrowRight size={14} />
                    </button>
                  )}
                </div>
              )}
              <footer className="components-footnote">
                <span>
                  <Info size={12} />
                  {t("模型输出为候选，请结合照片确认。分解视图用于解释组成。")}
                </span>
                {hiddenIds.size > 0 && (
                  <button
                    className="text-button"
                    onClick={() => setHiddenIds(new Set())}
                  >
                    {t("显示全部组件")}
                  </button>
                )}
              </footer>
            </section>

            <aside className="notes-panel">
              <div className="notes-title">
                <Info size={16} />
                <h2>{t("如何理解这个结果")}</h2>
              </div>
              <p>
                {t(
                  "这是基于照片的结构示意。组件厚度和背面使用简化先验，尚未标定真实尺寸。",
                )}
              </p>
              <div className="note-rule" />
              <p className="secondary-note">
                {t(
                  "候选组件不等同于完整工程 BOM；分解位置不代表真实拆装步骤。",
                )}
              </p>
              {Boolean(state.result?.warnings.length) && (
                <details className="result-warnings">
                  <summary>
                    {t("处理说明（{count}）", {
                      count: state.result?.warnings.length ?? 0,
                    })}
                  </summary>
                  <ul>
                    {state.result?.warnings.map((warning, index) => (
                      <li key={index}>{localize(warning)}</li>
                    ))}
                  </ul>
                </details>
              )}
              <div className="download-actions">
                <a
                  className={`download-link ${!state.result?.scene_url ? "disabled" : ""}`}
                  href={state.result?.scene_url || undefined}
                  download
                  aria-disabled={!state.result?.scene_url}
                >
                  <ArrowDownToLine size={14} />
                  {t("GLB 模型")}
                </a>
                <a
                  className={`download-link ${!state.result ? "disabled" : ""}`}
                  href={state.result?.json_url}
                  download
                  aria-disabled={!state.result}
                >
                  <FileJson size={14} />
                  {t("组件 JSON")}
                </a>
              </div>
            </aside>
          </div>
          <footer className="workspace-footer">
            <span>
              <span className="tiny-dot" />
              {t("本地文件与本地推理服务")}
            </span>
            <span>
              PV STRUCTURE <span className="footer-slash">/</span> {t("工作台")}{" "}
              v3.0.0
            </span>
          </footer>
        </main>
      </div>
      {multiOpened && (
        <div hidden={captureMode !== "multiview"}>
          <MultiviewWorkbench
            apiClient={apiClient}
            onBusyChange={setMultiBusy}
          />
        </div>
      )}
    </div>
  );
}

export default function App(props: { apiClient?: WorkbenchApi }) {
  return (
    <I18nProvider>
      <Workbench {...props} />
    </I18nProvider>
  );
}
