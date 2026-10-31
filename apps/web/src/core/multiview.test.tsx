import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useMultiview } from "./multiview";
import { asset, fakeApi, multiCompleted, multiRunning } from "../test/fixtures";
import type { Asset, MultiJobInput } from "../api/types";

const photos = ["front", "side"].map(
  (name) => new File([name], `${name}.png`, { type: "image/png" }),
);
afterEach(() => vi.useRealTimers());

it("requires 2–8 photos and starts only on explicit fusion", async () => {
  const create = vi.fn(async () => multiCompleted);
  const { result } = renderHook(() =>
    useMultiview(fakeApi({ createMultiJob: create })),
  );
  act(() => result.current.selectFiles(photos.slice(0, 1)));
  await act(async () => {
    await result.current.start();
  });
  expect(create).not.toHaveBeenCalled();
  act(() => result.current.selectFiles(photos));
  expect(result.current.state.files).toHaveLength(2);
  expect(create).not.toHaveBeenCalled();
  act(() => result.current.removeFile(1));
  expect(result.current.state.files).toHaveLength(1);
  act(() =>
    result.current.selectFiles(
      Array.from({ length: 9 }, (_, i) => photos[i % 2]),
    ),
  );
  expect(result.current.state.error).toBeTruthy();
});

it("uploads each photo, polls actual stages and submits only server mask references for manual jobs", async () => {
  vi.useFakeTimers();
  const submitted: MultiJobInput[] = [];
  const upload = vi.fn(async () => ({
    ...asset,
    id: `asset-${upload.mock.calls.length}`,
  }));
  const { result } = renderHook(() =>
    useMultiview(
      fakeApi({
        uploadAsset: upload,
        createMultiJob: async (input) => {
          submitted.push(input);
          return multiRunning;
        },
        getMultiJob: async () => multiCompleted,
      }),
    ),
  );
  act(() => result.current.selectFiles(photos));
  act(() => {
    void result.current.start();
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(700);
  });
  expect(upload).toHaveBeenCalledTimes(2);
  expect(result.current.state.result?.point_count).toBe(10);
  act(() => result.current.viewerReady());
  expect(result.current.state.phase).toBe("ready");
  act(() => {
    void result.current.rebuild([
      {
        ...multiCompleted.result!.observations[0],
        refinement_id: "ref",
        labelEdited: true,
      },
    ]);
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(700);
  });
  expect(submitted[1].base_job_id).toBe(multiCompleted.id);
  expect(submitted[1].observations?.[0]).not.toHaveProperty("labelEdited");
  expect(submitted[1].observations?.[0].refinement_id).toBe("ref");
});

it("cancellation ignores a late upload and preserves a newer group", async () => {
  let release!: (value: Asset) => void;
  const api = fakeApi({
    uploadAsset: () =>
      new Promise((resolve) => {
        release = resolve;
      }),
  });
  const { result } = renderHook(() => useMultiview(api));
  act(() => result.current.selectFiles(photos));
  act(() => {
    void result.current.start();
  });
  act(() => result.current.cancel());
  act(() => result.current.selectFiles([...photos].reverse()));
  await act(async () => {
    release(asset);
  });
  expect(result.current.state.files[0].name).toBe("side.png");
  expect(result.current.state.capture).toBeNull();
});
