import {
  AlertCircle,
  Check,
  Clock3,
  LoaderCircle,
  ScanLine,
  X,
} from "lucide-react";
import type { WorkbenchState } from "../core/workflow";
import { TaskProgress } from "./TaskProgress";
import { useI18n } from "../i18n";

const stageLabels: Record<string, string> = {
  queued: "任务已排队",
  starting: "正在准备识别任务",
  manual_components: "正在应用组件校正",
  loading: "正在载入识别模型",
  loading_model: "正在载入识别模型",
  detecting: "正在识别可见组件",
  recognition: "正在识别可见组件",
  grounding: "正在识别可见组件",
  loading_segmentation: "正在载入区域分割模型",
  segmenting: "正在提取组件区域",
  segmentation: "正在提取组件区域",
  geometry: "正在构建结构示意",
  building: "正在构建结构示意",
  exporting: "正在导出三维组件",
  complete: "结构已就绪",
  completed: "结构已就绪",
};

export function ProcessingStatus({
  state,
  elapsedMs,
  viewerError,
  onCancel,
  onRetry,
}: {
  state: WorkbenchState;
  elapsedMs: number;
  viewerError: string | null;
  onCancel: () => void;
  onRetry: () => void;
}) {
  const { t, localize, locale } = useI18n();
  const active = ["uploading", "processing", "preparing"].includes(state.phase);
  let title = "从一张照片开始";
  let subtitle = "照片上传后将自动识别，结果保留为可校正的组件候选。";
  if (state.phase === "uploading") {
    title = "正在上传并校验照片";
    subtitle = "正在检查格式、图像大小与方向。";
  }
  if (state.phase === "processing") {
    title =
      stageLabels[state.job?.stage || ""] ||
      (state.mode === "manual" ? "正在应用组件校正" : "正在准备识别任务");
    subtitle =
      state.mode === "manual"
        ? "根据校正后的组件重新构建结构，保留对应关系。"
        : ["loading", "loading_model", "loading_segmentation"].includes(
              state.job?.stage || "",
            )
          ? "首次载入或下载模型可能较久，准备完成后将自动继续。"
          : "各阶段耗时随图片和设备变化，处理进度会持续更新。";
  }
  if (state.phase === "preparing") {
    title = "正在载入三维结构";
    subtitle = "组件文件已生成，正在准备可旋转的视图。";
  }
  if (state.phase === "ready") {
    title = viewerError ? "结构文件已生成，查看器暂不可用" : "结构示意已就绪";
    subtitle = "点击照片、模型或列表中的组件，可联动选中。";
  }
  if (state.phase === "review") {
    title = "需要人工确认组件";
    subtitle = "本次未生成有效结构。可在照片上框出组件，再重新生成。";
  }
  if (state.phase === "cancelled") {
    title = "已停止等待此任务";
    subtitle = "已上传的照片仍可框选。后端任务可能继续完成。";
  }
  if (state.phase === "error") {
    title = "处理未完成";
    subtitle = state.error || "请重试，或在照片上人工框选组件。";
  }
  return (
    <>
      <div
        className={`processing-status status-${state.phase}`}
        role={state.phase === "error" ? "alert" : "status"}
        aria-live="polite"
      >
        <div className="processing-symbol">
          {active ? (
            <LoaderCircle className="spin" size={20} />
          ) : state.phase === "ready" && !viewerError ? (
            <Check size={20} />
          ) : ["error", "review"].includes(state.phase) || viewerError ? (
            <AlertCircle size={20} />
          ) : (
            <ScanLine size={20} />
          )}
        </div>
        <div className="processing-copy">
          <strong>{localize(title)}</strong>
          <p>{localize(subtitle)}</p>
        </div>
        <div className="processing-time">
          <span>
            <Clock3 size={14} />
            {state.startedAt === null
              ? t("按阶段显示处理进度")
              : t("已用 {seconds} 秒", {
                  seconds: new Intl.NumberFormat(locale, {
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1,
                  }).format(elapsedMs / 1000),
                })}
          </span>
          <small>
            {state.startedAt === null
              ? t("包含上传、推理与视图载入")
              : active
                ? t("正在持续处理")
                : t("本次端到端用时")}
          </small>
        </div>
        {active && (
          <button
            className="icon-button"
            aria-label={t("停止等待任务")}
            title={t("停止等待")}
            onClick={onCancel}
          >
            <X size={17} />
          </button>
        )}
        {["error", "cancelled", "review"].includes(state.phase) &&
          state.asset && (
            <button className="button small secondary" onClick={onRetry}>
              {t("重新识别")}
            </button>
          )}
      </div>
      <TaskProgress state={state} viewerError={viewerError} />
    </>
  );
}
