import type { Asset, Component, Job, Result, WorkbenchApi } from "../api/types";

export const asset: Asset = {
  id: "asset-1",
  width: 1000,
  height: 500,
  image_url: "/api/assets/asset-1/image",
  sha256: "abc",
};
export const cabinet: Component = {
  id: "cabinet-1",
  category: "cabinet",
  label: "逆变器机柜",
  bbox: [0.1, 0.1, 0.5, 0.9],
  score: 0.8,
  source: "grounding_dino",
  primitive: "box",
  color: "#8aa2a2",
  position: [0, 0, 0],
  dimensions: [1, 2, 0.3],
  node_name: "cabinet-1",
};
export const bracket: Component = {
  ...cabinet,
  id: "bracket-2",
  category: "bracket",
  label: "安装支架",
  bbox: [0.55, 0.2, 0.9, 0.8],
  node_name: "bracket-2",
};
export const result: Result = {
  job_id: "job-1",
  asset_id: "asset-1",
  equipment_type: "string_inverter",
  representation: "structural_schematic",
  metric_scale_status: "unknown",
  components: [cabinet, bracket],
  scene_url: "/api/jobs/job-1/scene.glb",
  json_url: "/api/jobs/job-1/result.json",
  warnings: [],
  model: { model_id: "grounding-dino" },
  timings: { inference_ms: 100 },
};
export const running: Job = {
  id: "job-1",
  asset_id: "asset-1",
  status: "running",
  stage: "detecting",
  created_at: "2026-10-30T00:00:00Z",
  elapsed_ms: 100,
  error: null,
  result: null,
};
export const completed: Job = {
  ...running,
  status: "succeeded",
  stage: "complete",
  result,
};

export function fakeApi(overrides: Partial<WorkbenchApi> = {}): WorkbenchApi {
  return {
    refine: async (input) => ({
      ...input,
      id: "test-refinement",
      geometry_bbox: input.bbox,
      mask_polygons: [
        [
          [input.bbox[0], input.bbox[1]],
          [input.bbox[2], input.bbox[1]],
          [input.bbox[2], input.bbox[3]],
        ],
      ],
      mask_url: "/api/refinements/test-refinement/mask.png",
      model: { model_id: "test-sam" },
      timings: {},
      warnings: [],
    }),
    health: async () => ({
      status: "ok",
      model: { state: "ready", model_id: "grounding-dino", device: "cpu" },
    }),
    uploadAsset: async () => asset,
    createJob: async () => running,
    getJob: async () => completed,
    getResult: async () => result,
    ...overrides,
  };
}
