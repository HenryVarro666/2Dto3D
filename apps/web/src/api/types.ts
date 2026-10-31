export type Category = "cabinet" | "bracket" | "pole" | "cables" | "unknown";
export type SceneMode = "single" | "multiple";
export type BBox = [number, number, number, number];
export type Point = [number, number];
export type ManualComponent = {
  id?: string;
  category: Category;
  label: string;
  bbox: BBox;
  refinement_id?: string | null;
};
export type EditableComponent = ManualComponent & {
  id: string;
  score?: number | null;
  source?: "grounding_dino" | "manual";
  color?: string;
  labelEdited?: boolean; // Local name provenance (false = system, true = user); never submitted.
  mask_polygon?: Point[] | null;
  mask_polygons?: Point[][] | null;
  mask_model?: Record<string, unknown> | null;
};
export type Component = EditableComponent & {
  score: number | null;
  source: "grounding_dino" | "manual";
  primitive: "box" | "cylinder" | "cable_bundle";
  color: string;
  position: [number, number, number];
  dimensions: [number, number, number];
  node_name: string;
};
export type Asset = {
  id: string;
  width: number;
  height: number;
  image_url: string;
  sha256: string;
};
export type Result = {
  job_id: string;
  asset_id: string;
  equipment_type: "string_inverter";
  scene_mode?: SceneMode;
  representation: "structural_schematic";
  metric_scale_status: "unknown";
  components: Component[];
  scene_url: string | null;
  json_url: string;
  warnings: string[];
  model: Record<string, unknown>;
  timings: Record<string, number>;
};
export type JobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "needs_review"
  | "failed"
  | "interrupted";
export type Job = {
  id: string;
  asset_id: string;
  status: JobStatus;
  stage: string;
  created_at: string;
  elapsed_ms: number;
  error: string | null;
  result: Result | null;
};
export type Health = {
  status: "ok";
  multiview?: {
    state: string;
    model_id?: string;
    device?: string;
    input_size?: number;
  };
  model: {
    state: string;
    model_id: string;
    device: string;
    error?: string | null;
  };
};
export type JobInput = {
  asset_id: string;
  mode?: "automatic" | "manual";
  scene_mode?: SceneMode;
  components?: ManualComponent[];
  base_job_id?: string;
};
export type PointPrompt = { x: number; y: number; label: 0 | 1 };
export type RefinementInput = {
  asset_id: string;
  bbox: BBox;
  points: PointPrompt[];
};
export type Refinement = RefinementInput & {
  id: string;
  geometry_bbox: BBox;
  mask_polygons: Point[][];
  mask_url: string;
  model: Record<string, unknown>;
  timings: Record<string, number>;
  warnings: string[];
};
export interface WorkbenchApi {
  refine(input: RefinementInput, signal?: AbortSignal): Promise<Refinement>;
  health(signal?: AbortSignal): Promise<Health>;
  uploadAsset(file: File, signal?: AbortSignal): Promise<Asset>;
  createJob(input: JobInput, signal?: AbortSignal): Promise<Job>;
  getJob(id: string, signal?: AbortSignal): Promise<Job>;
  getResult(id: string, signal?: AbortSignal): Promise<Result>;
  createCapture(assetIds: string[], signal?: AbortSignal): Promise<Capture>;
  getCapture(id: string, signal?: AbortSignal): Promise<Capture>;
  createMultiJob(input: MultiJobInput, signal?: AbortSignal): Promise<MultiJob>;
  getMultiJob(id: string, signal?: AbortSignal): Promise<MultiJob>;
}

export type Capture = { id: string; assets: Asset[]; created_at: string };
export type ViewObservation = EditableComponent & {
  asset_id: string;
  component_id: string;
};
export type MultiComponent = {
  id: string;
  category: Category;
  label: string;
  source: "grounding_dino" | "manual";
  score: number | null;
  observation_ids: string[];
  point_count: number;
  color: string;
  position: [number, number, number];
  dimensions: [number, number, number];
};
export type MultiResult = {
  job_id: string;
  capture_id: string;
  geometry_job_id: string;
  representation: "fused_point_cloud";
  metric_scale_status: "unknown";
  views: Asset[];
  observations: ViewObservation[];
  components: MultiComponent[];
  scene_url: string | null;
  ply_url: string | null;
  json_url: string;
  point_count: number;
  context_point_count: number;
  model: Record<string, unknown>;
  quality: Record<string, unknown>;
  timings: Record<string, number>;
  warnings: string[];
};
export type MultiJob = Omit<Job, "asset_id" | "result"> & {
  capture_id: string;
  view_index: number;
  total_views: number;
  result: MultiResult | null;
};
export type MultiJobInput = {
  capture_id: string;
  mode?: "automatic" | "manual";
  base_job_id?: string;
  observations?: (ManualComponent & {
    id: string;
    asset_id: string;
    component_id?: string;
  })[];
};
