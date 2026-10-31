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
import type { BBox, EditableComponent, WorkbenchApi } from "./api/types";
import { useWorkbench } from "./core/workflow";
import { ComponentList } from "./components/ComponentList";
import { ModelHealth } from "./components/ModelHealth";
import { PhotoPanel } from "./components/PhotoPanel";
import { ProcessingStatus } from "./components/ProcessingStatus";

const SceneViewer = lazy(() =>
  import("./components/SceneViewer").then((module) => ({
    default: module.SceneViewer,
  })),
);

export default function App({ apiClient = api }: { apiClient?: WorkbenchApi }) {
  const { state, elapsedMs, selectPhoto, rebuild, cancel, viewerReady } =
    useWorkbench(apiClient);
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
    setComponents(state.result.components);
    setHiddenIds(new Set());
    setSelectedId(null);
    setDirty(false);
    setExplosion(0);
    setViewerError(null);
  }, [state.result]);

  function chooseFile(file: File) {
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
  function addBox(bbox: BBox) {
    if (active || !state.asset) return;
    const id = `manual-${crypto.randomUUID()}`;
    setComponents((current) => [
      ...current,
      {
        id,
        bbox,
        category: "unknown",
        label: `新组件 ${current.length + 1}`,
        source: "manual",
        score: null,
        color: "#bc9563",
      },
    ]);
    setSelectedId(id);
    setEditRequestId(id);
    setDirty(true);
    setDrawing(false);
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
    if (active) return;
    setDrawing(false);
    setViewerError(null);
    void rebuild(
      components.map(({ id, category, label, bbox }) => ({
        id,
        category,
        label: label.trim(),
        bbox,
      })),
    );
  }
  const completedStep = state.result ? 3 : state.asset ? 2 : preview ? 1 : 0;
  const imageUrl = state.asset?.image_url || preview;
  const selected = components.find((item) => item.id === selectedId);
  const canDraw = Boolean(state.asset) && !active;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="PV Structure 工作台首页">
          <span className="brand-mark">
            <Box size={24} strokeWidth={1.7} />
          </span>
          <span>
            PV<span className="brand-light">STRUCTURE</span>
          </span>
          <small>设备结构实验室</small>
        </a>
        <div className="topbar-meta">
          <span className="local-badge">
            <span />
            LOCAL WORKSPACE
          </span>
          <span className="topbar-divider" />
          <span className="phase-badge">PHASE 01</span>
        </div>
      </header>
      <main className="main-content">
        <div className="workspace-heading">
          <div>
            <div className="breadcrumb">
              工作空间 <ChevronRight size={12} />
              <span>照片 → 组件结构</span>
            </div>
            <h1>
              设备结构工作台<span aria-hidden="true">一期</span>
            </h1>
            <p>组串式逆变器与外部安装结构的可交互示意</p>
          </div>
          <div className="workspace-actions">
            <ModelHealth api={apiClient} />
            <button
              className="button secondary upload-button"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload size={16} />
              {imageUrl ? "更换照片" : "导入照片"}
            </button>
          </div>
        </div>
        <input
          className="visually-hidden"
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          aria-label="选择设备照片"
          onChange={(event) => {
            const file = event.currentTarget.files?.[0];
            if (file) chooseFile(file);
            event.currentTarget.value = "";
          }}
        />

        <nav className="workflow-steps" aria-label="处理步骤">
          {[
            ["导入照片", "单张现场照片"],
            ["识别组件", "可见组件候选"],
            ["查看结构", "独立组件示意"],
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
              {index < 2 && <ChevronRight className="step-chevron" size={15} />}
            </div>
          ))}
          <span className="workflow-scope">
            <span className="tiny-dot" />
            单图 · 相对尺度 · 可人工校正
          </span>
        </nav>

        <ProcessingStatus
          state={state}
          elapsedMs={elapsedMs}
          viewerError={viewerError}
          onCancel={cancel}
          onRetry={() => {
            setDrawing(false);
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
            onDrawingChange={(value) => setDrawing(value && canDraw)}
            onBox={addBox}
          />

          <section
            className="view-panel model-panel"
            aria-labelledby="model-title"
          >
            <header className="panel-heading">
              <div>
                <span className="panel-index">02</span>
                <h2 id="model-title">三维结构</h2>
                <span className="panel-heading-note">STRUCTURE VIEW</span>
              </div>
              <span className="schematic-badge">结构示意 · 比例估计</span>
            </header>
            <div className="model-stage">
              {state.result?.scene_url ? (
                <Suspense
                  fallback={
                    <div className="viewer-loading">正在准备三维查看器…</div>
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
                    {active ? "正在准备组件结构" : "在这里查看设备的组成"}
                  </h3>
                  <p>
                    {active
                      ? "识别完成后，三维视图将自动载入"
                      : "上传照片后，旋转、选择并逐个查看组件"}
                  </p>
                  <div className="empty-interactions">
                    <span>
                      <RotateCcw size={13} />
                      旋转
                    </span>
                    <span>
                      <Focus size={13} />
                      选中
                    </span>
                    <span>
                      <Layers3 size={13} />
                      分解
                    </span>
                  </div>
                </div>
              )}
              <span className="scale-badge">
                <Info size={12} />
                尺寸未标定
              </span>
              {selected && (
                <div className="selected-component">
                  <span style={{ background: selected.color || "#719c92" }} />
                  <strong>{selected.label}</strong>
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
                    只看此组件 <Focus size={12} />
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
                  恢复视图
                </button>
                <label className="wireframe-toggle">
                  <input
                    type="checkbox"
                    checked={wireframe}
                    disabled={!state.result?.scene_url}
                    onChange={(event) => setWireframe(event.target.checked)}
                  />
                  线框
                </label>
              </div>
              <label className="explosion-control">
                <Layers3 size={14} />
                <span>组件分解</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={explosion}
                  disabled={!state.result?.scene_url}
                  onChange={(event) => setExplosion(Number(event.target.value))}
                  aria-label="组件分解程度"
                />
                <span className="explosion-value">
                  {Math.round(explosion * 100)}%
                </span>
              </label>
            </div>
            <footer className="model-caption">
              <span>拖动旋转 · 右键平移 · 滚轮缩放</span>
              <span>Y ↑</span>
            </footer>
          </section>
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
                <h2 id="components-title">组件候选</h2>
                <span className="count-badge">
                  {String(components.length).padStart(2, "0")}
                </span>
                {dirty && <span className="dirty-badge">校正待生成</span>}
              </div>
              <div className="component-heading-actions">
                <button
                  className={`text-button ${drawing ? "active" : ""}`}
                  disabled={!canDraw}
                  onClick={() => setDrawing(!drawing)}
                >
                  <ScanLine size={14} />
                  添加组件框
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
                  重新生成结构
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
                  if (active) return;
                  setComponents((current) =>
                    current.map((item) =>
                      item.id === id ? { ...item, ...patch } : item,
                    ),
                  );
                  setDirty(true);
                }}
                onRemove={(id) => {
                  if (active) return;
                  setComponents((current) =>
                    current.filter((item) => item.id !== id),
                  );
                  setDirty(true);
                  if (selectedId === id) setSelectedId(null);
                }}
                editRequestId={editRequestId}
                mutationsDisabled={active}
              />
            ) : (
              <div className="components-empty">
                <span>
                  <Layers3 size={25} strokeWidth={1.3} />
                </span>
                <div>
                  <strong>还没有组件候选</strong>
                  <p>
                    {state.asset && !active
                      ? "未识别到组件时，可在照片上手动框选并命名。"
                      : "照片中的可见机柜、安装支架和线缆会列在这里。"}
                  </p>
                </div>
                {state.asset && !active && (
                  <button
                    className="text-button"
                    onClick={() => setDrawing(true)}
                  >
                    开始框选 <ArrowRight size={14} />
                  </button>
                )}
              </div>
            )}
            <footer className="components-footnote">
              <span>
                <Info size={12} />
                模型输出为候选，请结合照片确认。分解视图用于解释组成。
              </span>
              {hiddenIds.size > 0 && (
                <button
                  className="text-button"
                  onClick={() => setHiddenIds(new Set())}
                >
                  显示全部组件
                </button>
              )}
            </footer>
          </section>

          <aside className="notes-panel">
            <div className="notes-title">
              <Info size={16} />
              <h2>如何理解这个结果</h2>
            </div>
            <p>
              这是基于照片的结构示意。组件厚度和背面使用简化先验，尚未标定真实尺寸。
            </p>
            <div className="note-rule" />
            <p className="secondary-note">
              候选组件不等同于完整工程 BOM；分解位置不代表真实拆装步骤。
            </p>
            {Boolean(state.result?.warnings.length) && (
              <details className="result-warnings">
                <summary>处理说明（{state.result?.warnings.length}）</summary>
                <ul>
                  {state.result?.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
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
                GLB 模型
              </a>
              <a
                className={`download-link ${!state.result ? "disabled" : ""}`}
                href={state.result?.json_url}
                download
                aria-disabled={!state.result}
              >
                <FileJson size={14} />
                组件 JSON
              </a>
            </div>
          </aside>
        </div>
        <footer className="workspace-footer">
          <span>
            <span className="tiny-dot" />
            本地文件与本地推理服务
          </span>
          <span>
            PV STRUCTURE <span className="footer-slash">/</span> 工作台 v0.1
          </span>
        </footer>
      </main>
    </div>
  );
}
