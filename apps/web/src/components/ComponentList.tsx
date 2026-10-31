import { useEffect, useState } from "react";
import { Crosshair, Pencil, Trash2, X } from "lucide-react";
import type { Category, EditableComponent } from "../api/types";
import { categoryKeys, useI18n } from "../i18n";
type Props = {
  components: EditableComponent[];
  selectedId: string | null;
  hiddenIds: Set<string>;
  onSelect: (id: string) => void;
  onToggle: (id: string) => void;
  onIsolate: (id: string) => void;
  onChange: (id: string, patch: Partial<EditableComponent>) => void;
  onRemove: (id: string) => void;
  editRequestId?: string | null;
  mutationsDisabled?: boolean;
};

export function ComponentList({
  components,
  selectedId,
  hiddenIds,
  onSelect,
  onToggle,
  onIsolate,
  onChange,
  onRemove,
  editRequestId,
  mutationsDisabled = false,
}: Props) {
  const { t, componentLabel } = useI18n();
  const [editingId, setEditingId] = useState<string | null>(null);
  useEffect(() => {
    if (editRequestId) setEditingId(editRequestId);
  }, [editRequestId]);
  const editing = components.find((item) => item.id === editingId);
  return (
    <>
      <div className="component-table">
        <div className="component-table-head">
          <span>{t("可见")}</span>
          <span>{t("组件候选")}</span>
          <span>{t("来源 / 模型分数")}</span>
          <span>{t("操作")}</span>
        </div>
        {components.map((component, index) => (
          <div
            className={`component-row ${selectedId === component.id ? "selected" : ""}`}
            key={component.id}
          >
            <label className="visibility-toggle">
              <input
                type="checkbox"
                aria-label={t("显示 {name}", {
                  name: componentLabel(component),
                })}
                checked={!hiddenIds.has(component.id)}
                onChange={() => onToggle(component.id)}
              />
              <span />
            </label>
            <button
              className="component-select"
              onClick={() => onSelect(component.id)}
              aria-label={t("选择 {name}", { name: componentLabel(component) })}
              aria-pressed={selectedId === component.id}
            >
              <span
                className="component-swatch"
                style={{ background: component.color || "#719c92" }}
              />
              <span>
                <strong>{componentLabel(component)}</strong>
                <small>
                  {String(index + 1).padStart(2, "0")} ·{" "}
                  {t(categoryKeys[component.category])}
                </small>
              </span>
            </button>
            <span
              className="component-confidence"
              title={
                component.source === "manual"
                  ? t("人工框选与命名")
                  : t("模型匹配分数未经准确率校准")
              }
            >
              {component.source === "manual" ? t("人工标注") : t("模型候选")}
              {component.score != null && (
                <small>{component.score.toFixed(2)}</small>
              )}
            </span>
            <div className="row-actions">
              <button
                className="icon-button"
                aria-label={t("只看 {name}", {
                  name: componentLabel(component),
                })}
                title={t("只看此组件")}
                onClick={() => onIsolate(component.id)}
              >
                <Crosshair size={15} />
              </button>
              <button
                className="icon-button"
                aria-label={t("编辑 {name}", {
                  name: componentLabel(component),
                })}
                title={t("编辑组件")}
                disabled={mutationsDisabled}
                onClick={() => {
                  onSelect(component.id);
                  setEditingId(component.id);
                }}
              >
                <Pencil size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
      {editing && (
        <div className="component-editor">
          <div className="editor-heading">
            <strong>{t("校正组件")}</strong>
            <code>{editing.id}</code>
            <button
              className="icon-button"
              aria-label={t("关闭组件编辑")}
              onClick={() => setEditingId(null)}
            >
              <X size={16} />
            </button>
          </div>
          <div className="editor-fields">
            <label>
              {t("组件名称")}
              <input
                aria-label={t("组件名称")}
                value={componentLabel(editing)}
                maxLength={80}
                disabled={mutationsDisabled}
                onChange={(event) =>
                  onChange(editing.id, { label: event.target.value })
                }
              />
            </label>
            <label>
              {t("组件类别")}
              <select
                aria-label={t("组件类别")}
                value={editing.category}
                disabled={mutationsDisabled}
                onChange={(event) =>
                  onChange(editing.id, {
                    category: event.target.value as Category,
                  })
                }
              >
                {Object.entries(categoryKeys).map(([value, label]) => (
                  <option key={value} value={value}>
                    {t(label)}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="text-button danger"
              disabled={mutationsDisabled}
              onClick={() => {
                onRemove(editing.id);
                setEditingId(null);
              }}
            >
              <Trash2 size={14} />
              {t("移除组件")}
            </button>
          </div>
          <p>
            {mutationsDisabled
              ? t("结构正在生成，完成后可继续校正。")
              : t(
                  "修改保留组件 ID。完成校正后，点击“重新生成结构”应用到三维示意。",
                )}
          </p>
        </div>
      )}
    </>
  );
}
