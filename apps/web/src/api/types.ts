export type Category = "cabinet" | "bracket" | "pole" | "cables" | "unknown";
export type BBox = [number, number, number, number];
export type Point = [number, number];
export type ManualComponent = {
  id?: string;
  category: Category;
  label: string;
  bbox: BBox;
};
export type EditableComponent = ManualComponent & {
  id: string;
  score?: number | null;
  source?: "grounding_dino" | "manual";
  color?: string;
  labelEdited?: boolean; // Local name provenance (false = system, true = user); never submitted.
};
export type Component = EditableComponent & {
  score: number | null;
  source: "grounding_dino" | "manual";
  primitive: "box" | "cylinder" | "cable_bundle";
  color: string;
  position: [number, number, number];
  dimensions: [number, number, number];
  node_name: string;
  mask_polygon?: Point[] | null;
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
  components?: ManualComponent[];
  base_job_id?: string;
};
export interface WorkbenchApi {
  health(signal?: AbortSignal): Promise<Health>;
  uploadAsset(file: File, signal?: AbortSignal): Promise<Asset>;
  createJob(input: JobInput, signal?: AbortSignal): Promise<Job>;
  getJob(id: string, signal?: AbortSignal): Promise<Job>;
  getResult(id: string, signal?: AbortSignal): Promise<Result>;
}
