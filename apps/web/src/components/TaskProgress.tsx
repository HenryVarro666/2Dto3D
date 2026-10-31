import {
  Check,
  Circle,
  LoaderCircle,
  Minus,
  Pause,
  AlertCircle,
} from "lucide-react";
import type { WorkbenchState } from "../core/workflow";

const automaticSteps = [
  "上传照片",
  "准备模型",
  "识别组件",
  "提取区域",
  "构建三维",
  "载入视图",
];
const manualSteps = ["应用组件校正", "构建三维", "载入视图"];
const automaticStages: Record<string, number> = {
  detecting: 2,
  recognition: 2,
  grounding: 2,
  loading_segmentation: 3,
  segmenting: 3,
  segmentation: 3,
  geometry: 4,
  building: 4,
  exporting: 4,
  complete: 5,
  completed: 5,
};
const manualStages: Record<string, number> = {
  geometry: 1,
  building: 1,
  exporting: 1,
  complete: 2,
  completed: 2,
};

export function TaskProgress({
  state,
  viewerError,
}: {
  state: WorkbenchState;
  viewerError: string | null;
}) {
  const manual = state.mode === "manual";
  const steps = manual ? manualSteps : automaticSteps;
  const active = ["uploading", "processing", "preparing"].includes(state.phase);
  const ready = state.phase === "ready" && !viewerError;
  const attention =
    ["error", "review"].includes(state.phase) || Boolean(viewerError);
  let completed =
    (manual ? manualStages : automaticStages)[state.job?.stage ?? ""] ??
    (manual || !state.asset ? 0 : 1);
  if (state.phase === "idle" || state.phase === "uploading") completed = 0;
  if (state.phase === "preparing" || state.phase === "ready")
    completed = steps.length - 1;
  if (state.phase === "review") completed = manual ? 0 : 2;
  if (ready) completed = steps.length;

  // A bypassed/failed optional segmenter must not appear as a completed model call.
  const segmentation =
    state.result?.job_id === state.job?.id
      ? state.result?.model.segmentation_state
      : undefined;
  const skippedRegion =
    !manual && (segmentation === "disabled" || segmentation === "unavailable");
  const unconfirmedRegion =
    !manual && completed > 3 && !skippedRegion && segmentation !== "ready";
  const currentLabel = ready
    ? "三维结构已就绪"
    : state.phase === "idle"
      ? "等待上传照片"
      : `${state.phase === "cancelled" ? "已停止于" : attention ? "待确认" : "当前"}：${steps[completed]}`;

  return (
    <section className="task-progress" aria-label="任务进度">
      <div className="task-progress-heading">
        <strong>{currentLabel}</strong>
        <span>
          {ready ? "全部完成" : `阶段 ${completed + 1} / ${steps.length}`} ·
          按处理阶段更新
        </span>
      </div>
      <div
        className="task-progress-track"
        role="progressbar"
        aria-label="处理阶段进度"
        aria-valuemin={0}
        aria-valuemax={steps.length}
        aria-valuenow={completed}
        aria-valuetext={currentLabel}
        aria-busy={active}
        style={{
          gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))`,
        }}
      >
        {steps.map((label, index) => (
          <span
            key={label}
            aria-hidden="true"
            className={
              skippedRegion && index === 3
                ? "skipped"
                : unconfirmedRegion && index === 3
                  ? "pending"
                  : index < completed
                    ? "complete"
                    : index === completed && active
                      ? "current"
                      : index === completed && attention
                        ? "attention"
                        : "pending"
            }
          />
        ))}
      </div>
      <ol
        className={`task-progress-steps ${manual ? "manual" : "automatic"}`}
        aria-label="处理阶段"
      >
        {steps.map((label, index) => {
          const skipped = skippedRegion && index === 3;
          const unconfirmed = unconfirmedRegion && index === 3;
          const passed = index < completed && !unconfirmed;
          const current = index === completed && state.phase !== "idle";
          const Icon = skipped
            ? Minus
            : passed
              ? Check
              : current && active
                ? LoaderCircle
                : current && attention
                  ? AlertCircle
                  : current && state.phase === "cancelled"
                    ? Pause
                    : Circle;
          const description = skipped
            ? "仅候选框"
            : unconfirmed
              ? active
                ? "等待结果"
                : "结果未确认"
              : passed
                ? "已完成"
                : current && active
                  ? "进行中"
                  : current && attention
                    ? "待确认"
                    : current && state.phase === "cancelled"
                      ? "已停止"
                      : "待处理";
          return (
            <li
              key={label}
              className={
                skipped
                  ? "skipped"
                  : passed
                    ? "complete"
                    : current
                      ? "current"
                      : "pending"
              }
              aria-current={current ? "step" : undefined}
            >
              <Icon
                size={14}
                aria-hidden="true"
                className={current && active && !skipped ? "spin" : undefined}
              />
              <span>
                {label}
                <small>{description}</small>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
