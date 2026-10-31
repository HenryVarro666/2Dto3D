import {
  Check,
  CornerUpLeft,
  LoaderCircle,
  Minus,
  Plus,
  RefreshCw,
  ScanLine,
  X,
} from "lucide-react";
import type { AnnotationController } from "../core/annotation";
import type { Category } from "../api/types";
import { categoryKeys, useI18n } from "../i18n";

export function AnnotationPanel({
  annotation,
  onConfirm,
  onRedraw,
}: {
  annotation: AnnotationController;
  onConfirm: (boxOnly: boolean) => void;
  onRedraw: () => void;
}) {
  const { t, localize, componentLabel, locale } = useI18n();
  const { draft, output, busy, error, pointMode, elapsedMs } = annotation;
  if (!draft) return null;
  return (
    <section className="annotation-panel" aria-label={t("边界细化草稿")}>
      <header>
        <div>
          <ScanLine size={18} />
          <h2>{t("边界细化草稿")}</h2>
          <span>{t("确认后加入组件")}</span>
        </div>
        <button
          className="icon-button"
          aria-label={t("取消边界细化")}
          onClick={annotation.cancel}
        >
          <X size={18} />
        </button>
      </header>
      <div className="annotation-fields">
        <label>
          {t("组件名称")}
          <input
            aria-label={t("补录组件名称")}
            value={componentLabel(draft.component)}
            maxLength={80}
            onChange={(event) =>
              annotation.update({ label: event.target.value })
            }
          />
        </label>
        <label>
          {t("组件类别")}
          <select
            aria-label={t("补录组件类别")}
            value={draft.component.category}
            onChange={(event) =>
              annotation.update({ category: event.target.value as Category })
            }
          >
            {Object.entries(categoryKeys).map(([key, label]) => (
              <option key={key} value={key}>
                {t(label)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="annotation-points-toolbar">
        <div
          className="point-mode-controls"
          role="group"
          aria-label={t("修正点类型")}
        >
          <button
            className={pointMode === 1 ? "active positive" : "positive"}
            aria-pressed={pointMode === 1}
            onClick={() => annotation.setPointMode(1)}
          >
            <Plus size={14} />
            {t("保留物体")}
          </button>
          <button
            className={pointMode === 0 ? "active negative" : "negative"}
            aria-pressed={pointMode === 0}
            onClick={() => annotation.setPointMode(0)}
          >
            <Minus size={14} />
            {t("排除背景")}
          </button>
        </div>
        <button
          className="text-button"
          disabled={!draft.points.length}
          onClick={annotation.undo}
        >
          <CornerUpLeft size={13} />
          {t("撤销一点")}
        </button>
        <button
          className="text-button"
          disabled={!draft.points.length}
          onClick={annotation.clearPoints}
        >
          {t("清空点")}
        </button>
        <button className="text-button" onClick={onRedraw}>
          {t("重新框选")}
        </button>
      </div>
      <p>{t("在左侧照片点击补点：绿色加号保留物体，红色减号排除背景。")}</p>
      <div className="annotation-state">
        {busy ? (
          <>
            <LoaderCircle size={16} className="spin" />
            <span role="status">{t("正在等待或细化边界…")}</span>
            <span>
              {t("已用 {seconds} 秒", {
                seconds: new Intl.NumberFormat(locale, {
                  minimumFractionDigits: 1,
                  maximumFractionDigits: 1,
                }).format(elapsedMs / 1000),
              })}
            </span>
          </>
        ) : error ? (
          <span role="alert">{localize(error)}</span>
        ) : output ? (
          <>
            <Check size={16} />
            <span role="status">
              {t("边界预览已更新，请确认是否覆盖目标物体。")}
            </span>
          </>
        ) : null}
      </div>
      {output?.warnings.map((warning, index) => (
        <p className="annotation-warning" key={index}>
          {localize(warning)}
        </p>
      ))}
      <footer>
        <span>{t("细化失败也可保留原框；厚度仍为估计。")}</span>
        <div>
          <button
            className="button small secondary"
            onClick={annotation.retry}
            disabled={busy}
          >
            <RefreshCw size={13} />
            {t("重试细化")}
          </button>
          <button
            className="button small secondary"
            onClick={() => onConfirm(true)}
            disabled={!draft.component.label.trim()}
          >
            {t("仅用框保存")}
          </button>
          <button
            className="button small primary"
            onClick={() => onConfirm(false)}
            disabled={busy || !output || !draft.component.label.trim()}
          >
            {t("确认区域")}
          </button>
        </div>
      </footer>
    </section>
  );
}
