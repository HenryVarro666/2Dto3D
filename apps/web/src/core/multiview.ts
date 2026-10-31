import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Capture,
  MultiJob,
  MultiJobInput,
  MultiResult,
  ViewObservation,
  WorkbenchApi,
} from "../api/types";
import type { Phase } from "./workflow";

export type MultiState = {
  files: File[];
  capture: Capture | null;
  job: MultiJob | null;
  result: MultiResult | null;
  phase: Phase;
  mode: "automatic" | "manual";
  error: string | null;
  uploadIndex: number;
  startedAt: number | null;
  finishedAt: number | null;
};
const initial: MultiState = {
  files: [],
  capture: null,
  job: null,
  result: null,
  phase: "idle",
  mode: "automatic",
  error: null,
  uploadIndex: 0,
  startedAt: null,
  finishedAt: null,
};
const terminal = new Set([
  "succeeded",
  "needs_review",
  "failed",
  "interrupted",
]);
const active = (phase: Phase) =>
  ["uploading", "processing", "preparing"].includes(phase);

function pollDelay(signal: AbortSignal): Promise<void> {
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

export function useMultiview(api: WorkbenchApi) {
  const [state, setState] = useState<MultiState>(initial);
  const [clock, setClock] = useState(Date.now);
  const current = useRef(state);
  current.current = state;
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  useEffect(
    () => () => {
      generation.current++;
      controller.current?.abort();
    },
    [],
  );
  useEffect(() => {
    if (state.startedAt === null || state.finishedAt !== null) return;
    const timer = setInterval(() => setClock(Date.now()), 100);
    return () => clearInterval(timer);
  }, [state.startedAt, state.finishedAt]);

  function selectFiles(files: File[]) {
    if (active(current.current.phase)) return;
    let error: string | null = null;
    if (files.length > 8) error = "每组最多 8 张照片。";
    else if (
      files.some(
        (f) => !["image/jpeg", "image/png", "image/webp"].includes(f.type),
      )
    )
      error = "请选择 JPEG、PNG 或 WebP 图片。";
    else if (files.some((f) => f.size > 20 * 1024 * 1024))
      error = "图片超过 20MB 上限，请选择较小的图片。";
    if (error) {
      setState((s) => ({ ...s, error }));
      return;
    }
    generation.current++;
    controller.current?.abort();
    setState({ ...initial, files });
  }
  function removeFile(index: number) {
    selectFiles(current.current.files.filter((_, i) => i !== index));
  }

  async function run(observations?: ViewObservation[]) {
    const previous = current.current;
    if (active(previous.phase)) return;
    if (previous.files.length < 2 || previous.files.length > 8) {
      setState((s) => ({
        ...s,
        error: "请选择同一设备的 2–8 张不同角度照片。",
      }));
      return;
    }
    if (observations && !previous.result) return;
    controller.current?.abort();
    const token = ++generation.current;
    const abort = new AbortController();
    controller.current = abort;
    const startedAt = Date.now();
    setClock(startedAt);
    setState((s) => ({
      ...s,
      phase: previous.capture ? "processing" : "uploading",
      mode: observations ? "manual" : "automatic",
      job: null,
      error: null,
      startedAt,
      finishedAt: null,
      uploadIndex: 0,
    }));
    try {
      let capture = previous.capture;
      if (!capture) {
        const assets = [];
        for (let i = 0; i < previous.files.length; i++) {
          setState((s) => ({ ...s, uploadIndex: i + 1 }));
          assets.push(await api.uploadAsset(previous.files[i], abort.signal));
          if (token !== generation.current) return;
        }
        capture = await api.createCapture(
          assets.map((a) => a.id),
          abort.signal,
        );
        if (token !== generation.current) return;
        setState((s) => ({ ...s, capture, phase: "processing" }));
      }
      const input: MultiJobInput = observations
        ? {
            capture_id: capture.id,
            mode: "manual",
            base_job_id: previous.result!.job_id,
            observations: observations.map(
              ({
                id,
                asset_id,
                component_id,
                category,
                label,
                bbox,
                refinement_id,
              }) => ({
                id,
                asset_id,
                component_id,
                category,
                label: label.trim(),
                bbox,
                ...(refinement_id !== undefined ? { refinement_id } : {}),
              }),
            ),
          }
        : { capture_id: capture.id, mode: "automatic" };
      let job = await api.createMultiJob(input, abort.signal);
      if (token !== generation.current) return;
      setState((s) => ({ ...s, phase: "processing", job }));
      while (!terminal.has(job.status)) {
        await pollDelay(abort.signal);
        job = await api.getMultiJob(job.id, abort.signal);
        if (token !== generation.current) return;
        setState((s) => ({ ...s, job }));
      }
      if (!job.result || ["failed", "interrupted"].includes(job.status))
        throw new Error(job.error || "多图处理未完成，请重试。");
      const result = job.result;
      setState((s) => ({
        ...s,
        job,
        result,
        phase: result.scene_url ? "preparing" : "review",
        finishedAt: result.scene_url ? null : Date.now(),
      }));
    } catch (error) {
      if (token !== generation.current || abort.signal.aborted) return;
      setState((s) => ({
        ...s,
        phase: "error",
        error:
          error instanceof Error ? error.message : "多图处理未完成，请重试。",
        finishedAt: Date.now(),
      }));
    }
  }
  const cancel = useCallback(() => {
    generation.current++;
    controller.current?.abort();
    setState((s) => ({ ...s, phase: "cancelled", finishedAt: Date.now() }));
  }, []);
  const viewerReady = useCallback(
    () =>
      setState((s) =>
        s.phase === "preparing"
          ? {
              ...s,
              phase: s.job?.status === "needs_review" ? "review" : "ready",
              finishedAt: Date.now(),
            }
          : s,
      ),
    [],
  );
  return {
    state,
    selectFiles,
    removeFile,
    start: () => run(),
    rebuild: (o: ViewObservation[]) => run(o),
    cancel,
    viewerReady,
    elapsedMs:
      state.startedAt === null
        ? 0
        : Math.max(0, (state.finishedAt ?? clock) - state.startedAt),
  };
}
