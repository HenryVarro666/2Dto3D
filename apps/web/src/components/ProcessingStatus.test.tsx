import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProcessingStatus } from "./ProcessingStatus";
import type { WorkbenchState } from "../core/workflow";
import { asset, completed, result, running } from "../test/fixtures";

function state(overrides: Partial<WorkbenchState> = {}): WorkbenchState {
  return {
    phase: "processing",
    mode: "automatic",
    asset,
    job: running,
    result: null,
    error: null,
    startedAt: 0,
    finishedAt: null,
    ...overrides,
  };
}

function status(current: WorkbenchState, viewerError: string | null = null) {
  return (
    <ProcessingStatus
      state={current}
      elapsedMs={15_000}
      viewerError={viewerError}
      onCancel={() => {}}
      onRetry={() => {}}
    />
  );
}

describe("phase-based processing progress", () => {
  it("reports actual detection stage after fifteen seconds without inventing completion", () => {
    render(status(state()));
    const progress = screen.getByRole("progressbar", { name: "处理阶段进度" });
    expect(progress).toHaveAttribute("aria-valuenow", "2");
    expect(progress).toHaveAttribute("aria-valuemax", "6");
    expect(progress).toHaveAttribute(
      "aria-valuetext",
      expect.stringContaining("识别组件"),
    );
    expect(screen.getByText("已用 15.0 秒")).toBeInTheDocument();
    expect(
      within(screen.getByRole("list", { name: "处理阶段" })).getAllByRole(
        "listitem",
      ),
    ).toHaveLength(6);
  });

  it("distinguishes loading the region model from extracting regions", () => {
    const view = render(
      status(state({ job: { ...running, stage: "loading_segmentation" } })),
    );
    expect(screen.getByText("正在载入区域分割模型")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "3",
    );
    view.rerender(status(state({ job: { ...running, stage: "segmenting" } })));
    expect(screen.getByText("正在提取组件区域")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "3",
    );
  });

  it("finishes only after the viewer is ready, not when the server returns a file", () => {
    const view = render(
      status(state({ phase: "preparing", job: completed, result })),
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "5",
    );
    view.rerender(status(state({ phase: "ready", job: completed, result })));
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "6",
    );
    view.rerender(
      status(
        state({ phase: "ready", job: completed, result }),
        "WebGL unavailable",
      ),
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "5",
    );
  });

  it.each(["error", "cancelled"] as const)(
    "retains the last stage without an active animation after %s",
    (phase) => {
      render(status(state({ phase, error: "设备暂不可用" })));
      expect(screen.getByRole("progressbar")).toHaveAttribute(
        "aria-valuenow",
        "2",
      );
      expect(screen.getByRole("progressbar")).toHaveAttribute(
        "aria-busy",
        "false",
      );
    },
  );

  it("uses a manual rebuild flow without claiming that model recognition ran", () => {
    render(
      status(state({ mode: "manual", job: { ...running, stage: "geometry" } })),
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuemax",
      "3",
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "1",
    );
    expect(
      screen.queryByText("识别组件", { exact: true }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/首次运行需要载入模型/)).not.toBeInTheDocument();
  });

  it.each(["processing", "error", "cancelled"] as const)(
    "does not assert a segmentation result before it exists during %s",
    (phase) => {
      render(status(state({ phase, job: { ...running, stage: "geometry" } })));
      const region = within(
        screen.getByRole("list", { name: "处理阶段" }),
      ).getAllByRole("listitem")[3];
      expect(within(region).queryByText("已完成")).not.toBeInTheDocument();
      expect(
        within(region).getByText(
          phase === "processing" ? "等待结果" : "结果未确认",
        ),
      ).toBeInTheDocument();
    },
  );

  it.each(["disabled", "unavailable"])(
    "marks optional segmentation as bbox-only when %s",
    (segmentation_state) => {
      render(
        status(
          state({
            phase: "ready",
            job: completed,
            result: {
              ...result,
              model: { ...result.model, segmentation_state },
            },
          }),
        ),
      );
      const region = within(
        screen.getByRole("list", { name: "处理阶段" }),
      ).getAllByRole("listitem")[3];
      expect(within(region).getByText("仅候选框")).toBeInTheDocument();
      expect(within(region).queryByText("已完成")).not.toBeInTheDocument();
    },
  );

  it("does not complete the 3D stages when no usable components were found", () => {
    render(
      status(
        state({
          phase: "review",
          job: { ...completed, status: "needs_review" },
          result: { ...result, components: [], scene_url: null },
        }),
      ),
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "2",
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-busy",
      "false",
    );
  });
});
