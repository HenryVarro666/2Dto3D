import { useEffect, useRef, useState } from "react";
import {
  ImagePlus,
  Maximize2,
  MousePointer2,
  ScanLine,
  Upload,
  X,
} from "lucide-react";
import type { Asset, BBox, EditableComponent, Point } from "../api/types";
import { useI18n } from "../i18n";
import type { AnnotationController } from "../core/annotation";
import {
  boxFromPoints,
  containedImageRect,
  normalizedPoint,
} from "../core/photoGeometry";

type Props = {
  imageUrl: string | null;
  fileName: string | null;
  asset: Asset | null;
  components: EditableComponent[];
  selectedId: string | null;
  hiddenIds: Set<string>;
  drawing: boolean;
  canDraw: boolean;
  onSelect: (id: string) => void;
  onChoose: () => void;
  onFile: (file: File) => void;
  onDrawingChange: (value: boolean) => void;
  onBox: (box: BBox) => void;
  annotation?: AnnotationController;
};

export function PhotoPanel({
  imageUrl,
  fileName,
  asset,
  components,
  selectedId,
  hiddenIds,
  drawing,
  canDraw,
  onSelect,
  onChoose,
  onFile,
  onDrawingChange,
  onBox,
  annotation,
}: Props) {
  const { t, componentLabel } = useI18n();
  const stageRef = useRef<HTMLDivElement>(null);
  const pointDown = useRef<Point | null>(null);
  const [panelSize, setPanelSize] = useState({ width: 0, height: 0 });
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [dragActive, setDragActive] = useState(false);
  const [showBoxes, setShowBoxes] = useState(true);
  const [drag, setDrag] = useState<{ start: Point; current: Point } | null>(
    null,
  );
  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const resize = () => {
      const rect = stage.getBoundingClientRect();
      setPanelSize({ width: rect.width, height: rect.height });
    };
    resize();
    const observer =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(resize) : null;
    observer?.observe(stage);
    window.addEventListener("resize", resize);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", resize);
    };
  }, []);
  useEffect(() => {
    setNaturalSize({ width: 0, height: 0 });
    setDrag(null);
  }, [imageUrl]);
  const fit = containedImageRect(
    panelSize.width,
    panelSize.height,
    asset?.width || naturalSize.width,
    asset?.height || naturalSize.height,
  );
  const currentBox = drag ? boxFromPoints(drag.start, drag.current) : null;
  const selected = components.find((item) => item.id === selectedId);
  const rings =
    selected?.mask_polygons ??
    (selected?.mask_polygon ? [selected.mask_polygon] : []);
  const pointAt = (event: React.PointerEvent<HTMLDivElement>): Point => {
    const rect = event.currentTarget.getBoundingClientRect();
    return normalizedPoint(event.clientX, event.clientY, {
      left: rect.left,
      top: rect.top,
      width: rect.width,
      height: rect.height,
    });
  };
  return (
    <section className="view-panel photo-panel" aria-labelledby="photo-title">
      <header className="panel-heading">
        <div>
          <span className="panel-index">01</span>
          <h2 id="photo-title">{t("原始照片")}</h2>
        </div>
        {imageUrl && (
          <button
            className="icon-button"
            title={t("打开规范化原图")}
            aria-label={t("打开原图")}
            onClick={() =>
              window.open(imageUrl, "_blank", "noopener,noreferrer")
            }
          >
            <Maximize2 size={15} />
          </button>
        )}
      </header>
      <div
        ref={stageRef}
        className={`photo-stage ${dragActive ? "drag-active" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          const file = event.dataTransfer.files[0];
          if (file) onFile(file);
        }}
      >
        {!imageUrl ? (
          <div className="upload-zone">
            <div className="upload-symbol">
              <ImagePlus size={32} strokeWidth={1.4} />
              <span className="symbol-corner corner-a" />
              <span className="symbol-corner corner-b" />
            </div>
            <h3>{t("拖入一张设备照片")}</h3>
            <p>{t("让机柜、支架和线缆尽量清晰可见")}</p>
            <button className="button primary" onClick={onChoose}>
              <Upload size={16} />
              {t("选择照片")}
            </button>
            <span className="upload-formats">
              {t("JPEG / PNG / WebP · 最大 20MB")}
            </span>
            <div className="upload-tip">
              <ScanLine size={15} />
              <span>{t("识别可见组件，生成独立的结构示意")}</span>
            </div>
          </div>
        ) : (
          <div
            className={`photo-fit ${drawing ? "is-drawing" : ""} ${annotation?.draft ? "is-annotating" : ""}`}
            style={
              fit.width
                ? {
                    left: fit.left,
                    top: fit.top,
                    width: fit.width,
                    height: fit.height,
                  }
                : { inset: 0 }
            }
            onPointerDown={(event) => {
              if (annotation?.draft) {
                event.preventDefault();
                pointDown.current = [event.clientX, event.clientY];
                return;
              }
              if (!drawing) return;
              event.preventDefault();
              event.currentTarget.setPointerCapture?.(event.pointerId);
              const start = pointAt(event);
              setDrag({ start, current: start });
            }}
            onPointerMove={(event) => {
              if (drawing && drag)
                setDrag({ ...drag, current: pointAt(event) });
            }}
            onPointerUp={(event) => {
              if (annotation?.draft) {
                const start = pointDown.current;
                pointDown.current = null;
                if (
                  start &&
                  Math.hypot(
                    event.clientX - start[0],
                    event.clientY - start[1],
                  ) <= 6
                )
                  annotation.addPoint(pointAt(event), annotation.pointMode);
                return;
              }
              if (!drawing || !drag) return;
              const bbox = boxFromPoints(drag.start, pointAt(event));
              setDrag(null);
              if (bbox) onBox(bbox);
            }}
            onPointerCancel={() => {
              setDrag(null);
              pointDown.current = null;
            }}
          >
            <img
              className="source-image"
              src={imageUrl}
              alt={t("待识别的组串式逆变器现场照片")}
              draggable={false}
              onLoad={(event) =>
                setNaturalSize({
                  width: event.currentTarget.naturalWidth,
                  height: event.currentTarget.naturalHeight,
                })
              }
            />
            {!annotation?.draft && !drawing && selected?.refinement_id && (
              <img
                className="photo-mask"
                alt=""
                draggable={false}
                src={`/api/refinements/${selected.refinement_id}/mask.png`}
              />
            )}
            {!annotation?.draft &&
              !drawing &&
              selected &&
              !selected.refinement_id &&
              rings.length > 0 && (
                <svg
                  className="photo-mask"
                  viewBox="0 0 1 1"
                  preserveAspectRatio="none"
                  aria-hidden="true"
                >
                  <path
                    d={rings
                      .map(
                        (ring) =>
                          `M${ring.map((point) => `${point[0]},${point[1]}`).join(" L")} Z`,
                      )
                      .join(" ")}
                    fill="rgba(24,150,114,.3)"
                    fillRule="evenodd"
                    stroke="#188b6a"
                    strokeWidth="1.5"
                    vectorEffect="non-scaling-stroke"
                  />
                </svg>
              )}
            {annotation?.draft && (
              <>
                {annotation.output && (
                  <img
                    className="photo-mask"
                    alt=""
                    draggable={false}
                    src={annotation.output.mask_url}
                  />
                )}
                <div
                  className="draft-box"
                  style={{
                    left: `${annotation.draft.box[0] * 100}%`,
                    top: `${annotation.draft.box[1] * 100}%`,
                    width: `${(annotation.draft.box[2] - annotation.draft.box[0]) * 100}%`,
                    height: `${(annotation.draft.box[3] - annotation.draft.box[1]) * 100}%`,
                  }}
                />
                {annotation.draft.points.map((point, index) => (
                  <span
                    className={`prompt-point ${point.label === 1 ? "positive" : "negative"}`}
                    key={index}
                    style={{
                      left: `${point.x * 100}%`,
                      top: `${point.y * 100}%`,
                    }}
                    aria-hidden="true"
                  >
                    {point.label === 1 ? "+" : "−"}
                  </span>
                ))}
              </>
            )}
            {showBoxes &&
              components.map((component, index) =>
                hiddenIds.has(component.id) ? null : (
                  <button
                    key={component.id}
                    className={`photo-box ${selectedId === component.id ? "selected" : ""}`}
                    style={
                      {
                        left: `${component.bbox[0] * 100}%`,
                        top: `${component.bbox[1] * 100}%`,
                        width: `${(component.bbox[2] - component.bbox[0]) * 100}%`,
                        height: `${(component.bbox[3] - component.bbox[1]) * 100}%`,
                        "--box-color": component.color || "#238773",
                      } as React.CSSProperties
                    }
                    onPointerDown={(event) => {
                      if (!drawing && !annotation?.draft)
                        event.stopPropagation();
                    }}
                    onClick={() => {
                      if (!drawing && !annotation?.draft)
                        onSelect(component.id);
                    }}
                    aria-label={t("照片中选择 {name}", {
                      name: componentLabel(component),
                    })}
                  >
                    <span>
                      {String(index + 1).padStart(2, "0")}{" "}
                      {componentLabel(component)}
                    </span>
                  </button>
                ),
              )}
            {currentBox && (
              <div
                className="drawing-box"
                style={{
                  left: `${currentBox[0] * 100}%`,
                  top: `${currentBox[1] * 100}%`,
                  width: `${(currentBox[2] - currentBox[0]) * 100}%`,
                  height: `${(currentBox[3] - currentBox[1]) * 100}%`,
                }}
              />
            )}
          </div>
        )}
        {imageUrl && drawing && (
          <div className="draw-hint">
            <ScanLine size={15} />
            {t("在照片上拖动，框出一个可见组件")}
            <button
              className="icon-button"
              aria-label={t("退出框选")}
              onClick={() => onDrawingChange(false)}
            >
              <X size={14} />
            </button>
          </div>
        )}
        {dragActive && (
          <div className="drop-overlay">
            <Upload size={28} />
            <strong>{t("松开以替换照片")}</strong>
          </div>
        )}
      </div>
      <footer className="photo-toolbar">
        {imageUrl ? (
          <>
            <span className="photo-filename" title={fileName || undefined}>
              {fileName || t("规范化照片")}
              {asset && (
                <small>
                  {asset.width} × {asset.height}
                </small>
              )}
            </span>
            <label className="boxes-toggle">
              <input
                type="checkbox"
                checked={showBoxes}
                onChange={(event) => setShowBoxes(event.target.checked)}
              />
              {t("候选框")}
            </label>
            <button
              className={`tool-button ${drawing ? "active" : ""}`}
              disabled={!canDraw}
              onClick={() => onDrawingChange(!drawing)}
            >
              <MousePointer2 size={14} />
              {drawing ? t("结束框选") : t("添加组件框")}
            </button>
          </>
        ) : (
          <span className="muted">
            <span className="tiny-dot" />
            {t("单张照片优先 · 一期支持组串式逆变器")}
          </span>
        )}
      </footer>
    </section>
  );
}
