import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useWorkbench } from "./workflow";
import { asset, cabinet, completed, fakeApi, running } from "../test/fixtures";
import type { Asset, Job, JobInput } from "../api/types";

const photo = new File(["real upload boundary"], "inverter.png", {
  type: "image/png",
});
const flush = async () => {
  await act(async () => {
    await Promise.resolve();
  });
};

describe("photo-to-scene workflow", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("polls until the terminal result, then stops while retaining the result", async () => {
    let pollCount = 0;
    const api = fakeApi({
      getJob: async () => (++pollCount === 1 ? running : completed),
    });
    const { result } = renderHook(() => useWorkbench(api));
    act(() => {
      void result.current.selectPhoto(photo);
    });
    await flush();
    expect(result.current.state.phase).toBe("processing");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1400);
    });
    expect(
      result.current.state.result?.components.map((item) => item.id),
    ).toEqual(["cabinet-1", "bracket-2"]);
    act(() => result.current.viewerReady());
    expect(result.current.state.phase).toBe("ready");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3500);
    });
    expect(pollCount).toBe(2);
  });

  it("stops scheduling polls after cancellation and keeps the uploaded photo available for correction", async () => {
    let pollCount = 0;
    const { result } = renderHook(() =>
      useWorkbench(
        fakeApi({
          getJob: async () => {
            pollCount += 1;
            return running;
          },
        }),
      ),
    );
    act(() => {
      void result.current.selectPhoto(photo);
    });
    await flush();
    act(() => result.current.cancel());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(result.current.state.phase).toBe("cancelled");
    expect(result.current.state.asset?.id).toBe("asset-1");
    expect(pollCount).toBe(0);
  });

  it("ignores an old upload even when its response arrives after a replacement photo", async () => {
    let resolveOld!: (value: Asset) => void;
    const oldUpload = new Promise<Asset>((resolve) => {
      resolveOld = resolve;
    });
    const api = fakeApi({
      uploadAsset: async (file) =>
        file.name === "old.png" ? oldUpload : { ...asset, id: "new-asset" },
      createJob: async (input) => ({
        ...running,
        asset_id: input.asset_id,
        id: input.asset_id,
      }),
    });
    const { result } = renderHook(() => useWorkbench(api));
    act(() => {
      void result.current.selectPhoto(
        new File(["old"], "old.png", { type: "image/png" }),
      );
    });
    act(() => {
      void result.current.selectPhoto(photo);
    });
    await flush();
    await act(async () => {
      resolveOld(asset);
    });
    expect(result.current.state.asset?.id).toBe("new-asset");
    expect(result.current.state.job?.id).toBe("new-asset");
  });

  it("shows model failures without discarding the image and permits manual rebuilding with stable IDs", async () => {
    let manualPayload: unknown;
    const failed: Job = {
      ...running,
      status: "failed",
      stage: "failed",
      error: "模型权重尚未就绪",
    };
    const api = fakeApi({
      getJob: async () => failed,
      createJob: async (input) => {
        if (input.mode === "manual") {
          manualPayload = input;
          return completed;
        }
        return running;
      },
    });
    const { result } = renderHook(() => useWorkbench(api));
    act(() => {
      void result.current.selectPhoto(photo);
    });
    await flush();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(700);
    });
    expect(result.current.state.error).toBe("模型权重尚未就绪");
    expect(result.current.state.asset?.id).toBe("asset-1");
    await act(async () => {
      await result.current.rebuild([
        {
          id: "kept-id",
          category: "cabinet",
          label: "机柜",
          bbox: [0.1, 0.1, 0.8, 0.9],
        },
      ]);
    });
    expect(manualPayload).toEqual({
      asset_id: "asset-1",
      mode: "manual",
      components: [
        {
          id: "kept-id",
          category: "cabinet",
          label: "机柜",
          bbox: [0.1, 0.1, 0.8, 0.9],
        },
      ],
    });
    expect(result.current.state.phase).toBe("preparing");
    expect(result.current.state.mode).toBe("manual");
    act(() => {
      void result.current.rebuild();
    });
    await flush();
    expect(result.current.state.mode).toBe("automatic");
  });

  it("continues showing actual elapsed time after ten seconds", async () => {
    const { result } = renderHook(() =>
      useWorkbench(fakeApi({ getJob: async () => running })),
    );
    act(() => {
      void result.current.selectPhoto(photo);
    });
    await flush();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(12_000);
    });
    expect(result.current.state.phase).toBe("processing");
    expect(result.current.elapsedMs).toBeGreaterThanOrEqual(12_000);
  });

  it("associates manual corrections with the current result without sending client provenance", async () => {
    let payload: JobInput | undefined;
    const { result } = renderHook(() =>
      useWorkbench(
        fakeApi({
          createJob: async (input) => {
            payload = input;
            return completed;
          },
        }),
      ),
    );
    await act(async () => {
      await result.current.selectPhoto(photo);
    });
    await act(async () => {
      await result.current.rebuild([{ ...cabinet, label: "校正机柜" }]);
    });

    expect(payload).toEqual({
      asset_id: "asset-1",
      mode: "manual",
      base_job_id: "job-1",
      components: [
        {
          id: "cabinet-1",
          category: "cabinet",
          label: "校正机柜",
          bbox: [0.1, 0.1, 0.5, 0.9],
        },
      ],
    });
  });

  it("does not attach a prior photo result as the base of a replacement photo correction", async () => {
    let payload: JobInput | undefined;
    const api = fakeApi({
      uploadAsset: async (file) =>
        file.name === "replacement.png"
          ? { ...asset, id: "replacement-asset" }
          : asset,
      createJob: async (input) => {
        payload = input;
        if (input.asset_id === "asset-1") return completed;
        return {
          ...running,
          id: "replacement-job",
          asset_id: "replacement-asset",
          status: "failed",
          error: "需要手动框选",
        };
      },
    });
    const { result } = renderHook(() => useWorkbench(api));
    await act(async () => {
      await result.current.selectPhoto(photo);
    });
    expect(result.current.state.result?.job_id).toBe("job-1");
    await act(async () => {
      await result.current.selectPhoto(
        new File(["new image"], "replacement.png", { type: "image/png" }),
      );
    });
    await act(async () => {
      await result.current.rebuild([
        {
          id: "replacement-box",
          category: "bracket",
          label: "新支架",
          bbox: [0.2, 0.2, 0.8, 0.8],
        },
      ]);
    });

    expect(payload).toEqual({
      asset_id: "replacement-asset",
      mode: "manual",
      components: [
        {
          id: "replacement-box",
          category: "bracket",
          label: "新支架",
          bbox: [0.2, 0.2, 0.8, 0.8],
        },
      ],
    });
  });
});
