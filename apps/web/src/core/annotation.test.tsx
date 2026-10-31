import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useAnnotation } from "./annotation";
import { asset, cabinet, fakeApi } from "../test/fixtures";
import type { Refinement, RefinementInput } from "../api/types";

const mask: Refinement = {
  id: "mask-1",
  asset_id: asset.id,
  bbox: [0.1, 0.1, 0.5, 0.9],
  geometry_bbox: [0.12, 0.12, 0.48, 0.88],
  points: [],
  mask_polygons: [
    [
      [0.12, 0.12],
      [0.48, 0.12],
      [0.48, 0.88],
    ],
  ],
  mask_url: "/api/refinements/mask-1/mask.png",
  model: { model_id: "sam2" },
  timings: {},
  warnings: [],
};
const settle = async () => {
  await act(async () => {
    await Promise.resolve();
  });
};
const tick = async () => {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(250);
  });
};
beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

it("automatically refines a box and confirms only server-derived geometry while preserving the component ID", async () => {
  let calls = 0;
  const { result } = renderHook(() =>
    useAnnotation(
      fakeApi({
        refine: async () => {
          calls += 1;
          return mask;
        },
      }),
    ),
  );
  act(() => result.current.start(asset, cabinet.bbox, cabinet));
  expect(result.current.confirm()).toBeNull();
  await tick();
  expect(result.current.output?.id).toBe("mask-1");
  act(() => result.current.update({ label: "New name", category: "cables" }));
  await tick();
  expect(calls).toBe(1); // Metadata edits must not rerun SAM.
  let component;
  act(() => {
    component = result.current.confirm();
  });
  expect(component).toMatchObject({
    id: "cabinet-1",
    label: "New name",
    category: "cables",
    bbox: [0.12, 0.12, 0.48, 0.88],
    refinement_id: "mask-1",
    source: "manual",
    score: null,
  });
  expect(result.current.draft).toBeNull();
});

it("coalesces point edits behind one request and cannot confirm a stale preview", async () => {
  const calls: RefinementInput[] = [];
  const resolves: ((value: Refinement) => void)[] = [];
  const { result } = renderHook(() =>
    useAnnotation(
      fakeApi({
        refine: async (input) => {
          calls.push(input);
          return new Promise((resolve) => resolves.push(resolve));
        },
      }),
    ),
  );
  act(() => result.current.start(asset, cabinet.bbox, cabinet));
  await tick();
  act(() => result.current.addPoint([0.2, 0.2], 1));
  act(() => result.current.addPoint([0.6, 0.6], 0));
  await tick();
  expect(calls).toHaveLength(1);
  await act(async () => resolves[0](mask));
  expect(result.current.output).toBeNull();
  expect(result.current.confirm()).toBeNull();
  await tick();
  expect(calls).toHaveLength(2);
  expect(calls[1].points).toEqual([
    { x: 0.2, y: 0.2, label: 1 },
    { x: 0.6, y: 0.6, label: 0 },
  ]);
  await act(async () => resolves[1]({ ...mask, id: "mask-latest" }));
  expect(result.current.output?.id).toBe("mask-latest");
  act(() => result.current.undo());
  expect(result.current.draft?.points).toEqual([{ x: 0.2, y: 0.2, label: 1 }]);
  act(() => result.current.clearPoints());
  expect(result.current.draft?.points).toEqual([]);
});

it("ignores late responses after cancellation and replacement with another photo", async () => {
  let resolveOld!: (value: Refinement) => void;
  const { result } = renderHook(() =>
    useAnnotation(
      fakeApi({
        refine: async (input) =>
          input.asset_id === asset.id
            ? new Promise((resolve) => {
                resolveOld = resolve;
              })
            : { ...mask, id: "new-mask", asset_id: "new-asset" },
      }),
    ),
  );
  act(() => result.current.start(asset, cabinet.bbox, cabinet));
  await tick();
  act(() => result.current.cancel());
  act(() =>
    result.current.start({ ...asset, id: "new-asset" }, cabinet.bbox, cabinet),
  );
  await tick();
  await act(async () => resolveOld(mask));
  await settle();
  expect(result.current.draft?.asset.id).toBe("new-asset");
  expect(result.current.output?.id).toBe("new-mask");
});

it("keeps the named draft after failure and can explicitly save just the box without fabricating a mask", async () => {
  const { result } = renderHook(() =>
    useAnnotation(
      fakeApi({
        refine: async () => {
          throw new Error("SAM unavailable");
        },
      }),
    ),
  );
  act(() => result.current.start(asset, cabinet.bbox, cabinet));
  act(() => result.current.update({ label: "Manual cabinet" }));
  await tick();
  expect(result.current.error).toBe("SAM unavailable");
  expect(result.current.draft?.component.label).toBe("Manual cabinet");
  let component;
  act(() => {
    component = result.current.confirm(true);
  });
  expect(component).toMatchObject({
    id: "cabinet-1",
    bbox: cabinet.bbox,
    refinement_id: null,
    mask_polygons: null,
    mask_polygon: null,
  });
});

it("rejects a positive point outside the box while retaining valid foreground and background prompts", async () => {
  const { result } = renderHook(() =>
    useAnnotation(fakeApi({ refine: async () => mask })),
  );
  act(() => result.current.start(asset, cabinet.bbox, cabinet));
  act(() => result.current.addPoint([0.9, 0.9], 1));
  expect(result.current.draft?.points).toHaveLength(0);
  act(() => result.current.addPoint([0.9, 0.9], 0));
  expect(result.current.draft?.points).toEqual([{ x: 0.9, y: 0.9, label: 0 }]);
});
