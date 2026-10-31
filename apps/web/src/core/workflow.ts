import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Asset,
  Job,
  ManualComponent,
  Result,
  WorkbenchApi,
  SceneMode,
} from "../api/types";

export type Phase =
  | "idle"
  | "uploading"
  | "processing"
  | "preparing"
  | "ready"
  | "review"
  | "error"
  | "cancelled";
export type WorkbenchState = {
  phase: Phase;
  mode: "automatic" | "manual";
  asset: Asset | null;
  job: Job | null;
  result: Result | null;
  error: string | null;
  startedAt: number | null;
  finishedAt: number | null;
};
const initialState: WorkbenchState = {
  phase: "idle",
  mode: "automatic",
  asset: null,
  job: null,
  result: null,
  error: null,
  startedAt: null,
  finishedAt: null,
};
const terminal = new Set([
  "succeeded",
  "needs_review",
  "failed",
  "interrupted",
]);

function waitForPoll(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const cancel = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", cancel);
      resolve();
    }, 700);
    signal.addEventListener("abort", cancel, { once: true });
    if (signal.aborted) cancel();
  });
}

export function useWorkbench(
  api: WorkbenchApi,
  sceneMode: SceneMode = "single",
) {
  const [state, setState] = useState<WorkbenchState>(initialState);
  const [clock, setClock] = useState(Date.now);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(
    () => () => {
      generation.current += 1;
      controller.current?.abort();
    },
    [],
  );
  useEffect(() => {
    if (state.startedAt === null || state.finishedAt !== null) return;
    const timer = setInterval(() => setClock(Date.now()), 100);
    return () => clearInterval(timer);
  }, [state.startedAt, state.finishedAt]);

  const begin = () => {
    controller.current?.abort();
    const token = ++generation.current;
    const abortController = new AbortController();
    controller.current = abortController;
    return { token, signal: abortController.signal };
  };

  async function runJob(
    asset: Asset,
    token: number,
    signal: AbortSignal,
    components?: ManualComponent[],
    baseJobId?: string,
  ) {
    let job = await api.createJob(
      components
        ? {
            asset_id: asset.id,
            mode: "manual",
            ...(sceneMode === "multiple" ? { scene_mode: sceneMode } : {}),
            components: components.map(
              ({ id, category, label, bbox, refinement_id }) => ({
                id,
                category,
                label,
                bbox,
                ...(refinement_id !== undefined ? { refinement_id } : {}),
              }),
            ),
            ...(baseJobId ? { base_job_id: baseJobId } : {}),
          }
        : {
            asset_id: asset.id,
            mode: "automatic",
            ...(sceneMode === "multiple" ? { scene_mode: sceneMode } : {}),
          },
      signal,
    );
    if (token !== generation.current) return;
    setState((current) => ({ ...current, phase: "processing", job }));
    while (!terminal.has(job.status)) {
      await waitForPoll(signal);
      job = await api.getJob(job.id, signal);
      if (token !== generation.current) return;
      setState((current) => ({ ...current, job }));
    }
    if (job.status === "failed" || job.status === "interrupted")
      throw new Error(
        job.error ||
          (job.status === "interrupted"
            ? "任务因服务重启而中断。可重新识别或手动框选。"
            : "识别未完成，可重试或手动框选组件。"),
      );
    const result = job.result ?? (await api.getResult(job.id, signal));
    if (token !== generation.current) return;
    setState((current) => ({
      ...current,
      job,
      result,
      phase: result.scene_url ? "preparing" : "review",
      finishedAt: result.scene_url ? null : Date.now(),
    }));
  }

  function fail(error: unknown, token: number) {
    if (token !== generation.current) return;
    if (error instanceof Error && error.name === "AbortError") return;
    setState((current) => ({
      ...current,
      phase: "error",
      error: error instanceof Error ? error.message : "请求未完成，请重试。",
      finishedAt: Date.now(),
    }));
  }

  async function selectPhoto(file: File) {
    const { token, signal } = begin();
    const startedAt = Date.now();
    setClock(startedAt);
    setState({ ...initialState, phase: "uploading", startedAt });
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      fail(new Error("请选择 JPEG、PNG 或 WebP 图片。"), token);
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      fail(new Error("图片超过 20MB 上限，请选择较小的图片。"), token);
      return;
    }
    try {
      const asset = await api.uploadAsset(file, signal);
      if (token !== generation.current) return;
      setState((current) => ({ ...current, asset, phase: "processing" }));
      await runJob(asset, token, signal);
    } catch (error) {
      fail(error, token);
    }
  }

  async function rebuild(components?: ManualComponent[]) {
    const asset = stateRef.current.asset;
    if (!asset) return;
    const priorResult = stateRef.current.result;
    const baseJobId =
      components && priorResult?.asset_id === asset.id
        ? priorResult.job_id
        : undefined;
    const { token, signal } = begin();
    const startedAt = Date.now();
    setClock(startedAt);
    setState((current) => ({
      ...current,
      phase: "processing",
      mode: components ? "manual" : "automatic",
      job: null,
      error: null,
      startedAt,
      finishedAt: null,
    }));
    try {
      await runJob(asset, token, signal, components, baseJobId);
    } catch (error) {
      fail(error, token);
    }
  }

  const cancel = useCallback(() => {
    generation.current += 1;
    controller.current?.abort();
    setState((current) => ({
      ...current,
      phase: "cancelled",
      finishedAt: Date.now(),
    }));
  }, []);
  const viewerReady = useCallback(
    () =>
      setState((current) =>
        current.phase === "preparing"
          ? { ...current, phase: "ready", finishedAt: Date.now() }
          : current,
      ),
    [],
  );
  const elapsedMs =
    state.startedAt === null
      ? 0
      : Math.max(0, (state.finishedAt ?? clock) - state.startedAt);
  return { state, elapsedMs, selectPhoto, rebuild, cancel, viewerReady };
}
