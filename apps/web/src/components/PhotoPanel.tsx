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
}: Props) {
  const stageRef = useRef<HTMLDivElement>(null);
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
          <h2 id="photo-title">原始照片</h2>
          <span className="panel-heading-note">SOURCE IMAGE</span>
        </div>
        {imageUrl && (
          <button
            className="icon-button"
            title="打开规范化原图"
            aria-label="打开原图"
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
            <h3>拖入一张设备照片</h3>
            <p>让机柜、支架和线缆尽量清晰可见</p>
            <button className="button primary" onClick={onChoose}>
              <Upload size={16} />
              选择照片
            </button>
            <span className="upload-formats">
              JPEG / PNG / WebP · 最大 20MB
            </span>
            <div className="upload-tip">
              <ScanLine size={15} />
              <span>识别可见组件，生成独立的结构示意</span>
            </div>
          </div>
        ) : (
          <div
            className={`photo-fit ${drawing ? "is-drawing" : ""}`}
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
              if (!drawing || !drag) return;
              const bbox = boxFromPoints(drag.start, pointAt(event));
              setDrag(null);
              if (bbox) onBox(bbox);
            }}
            onPointerCancel={() => setDrag(null)}
          >
            <img
              src={imageUrl}
              alt="待识别的组串式逆变器现场照片"
              draggable={false}
              onLoad={(event) =>
                setNaturalSize({
                  width: event.currentTarget.naturalWidth,
                  height: event.currentTarget.naturalHeight,
                })
              }
            />
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
                      if (!drawing) event.stopPropagation();
                    }}
                    onClick={() => {
                      if (!drawing) onSelect(component.id);
                    }}
                    aria-label={`照片中选择 ${component.label}`}
                  >
                    <span>
                      {String(index + 1).padStart(2, "0")} {component.label}
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
            在照片上拖动，框出一个可见组件
            <button
              className="icon-button"
              aria-label="退出框选"
              onClick={() => onDrawingChange(false)}
            >
              <X size={14} />
            </button>
          </div>
        )}
        {dragActive && (
          <div className="drop-overlay">
            <Upload size={28} />
            <strong>松开以替换照片</strong>
          </div>
        )}
      </div>
      <footer className="photo-toolbar">
        {imageUrl ? (
          <>
            <span className="photo-filename" title={fileName || undefined}>
              {fileName || "规范化照片"}
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
              候选框
            </label>
            <button
              className={`tool-button ${drawing ? "active" : ""}`}
              disabled={!canDraw}
              onClick={() => onDrawingChange(!drawing)}
            >
              <MousePointer2 size={14} />
              {drawing ? "结束框选" : "添加组件框"}
            </button>
          </>
        ) : (
          <span className="muted">
            <span className="tiny-dot" />
            单张照片优先 · 一期支持组串式逆变器
          </span>
        )}
      </footer>
    </section>
  );
}
