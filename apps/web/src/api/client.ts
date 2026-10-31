import type {
  Asset,
  Health,
  Job,
  JobInput,
  Result,
  WorkbenchApi,
} from "./types";

export function createApi(): WorkbenchApi {
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`/api${path}`, init);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") throw error;
      throw new Error("无法连接本地服务，请检查 API 是否已启动，再重试。");
    }
    if (!response.ok) {
      const data = (await response.json().catch(() => null)) as {
        detail?: unknown;
        error?: unknown;
      } | null;
      const detail = data?.detail ?? data?.error;
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail
                .map((item: { msg?: string }) => item.msg ?? "参数无效")
                .join("；")
            : `请求未完成（${response.status}），请重试。`;
      throw new Error(message);
    }
    return response.json() as Promise<T>;
  }
  return {
    health: (signal) => request<Health>("/health", { signal }),
    uploadAsset: (file, signal) => {
      const body = new FormData();
      body.append("file", file);
      return request<Asset>("/assets", { method: "POST", body, signal });
    },
    createJob: (input: JobInput, signal) =>
      request<Job>("/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
        signal,
      }),
    getJob: (id, signal) =>
      request<Job>(`/jobs/${encodeURIComponent(id)}`, { signal }),
    getResult: (id, signal) =>
      request<Result>(`/jobs/${encodeURIComponent(id)}/result`, { signal }),
  };
}

export const api = createApi();
