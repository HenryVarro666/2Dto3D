import { useEffect, useState } from "react";
import { CircleHelp } from "lucide-react";
import type { Health, WorkbenchApi } from "../api/types";

const stateLabels: Record<string, string> = {
  unloaded: "模型待载入",
  not_loaded: "模型待载入",
  idle: "模型待载入",
  loading: "模型载入中",
  downloading: "模型下载中",
  ready: "模型已就绪",
  loaded: "模型已就绪",
  error: "模型不可用",
  failed: "模型不可用",
  unavailable: "模型不可用",
};

export function ModelHealth({ api }: { api: WorkbenchApi }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const next = await api.health(controller.signal);
        if (!controller.signal.aborted) {
          setHealth(next);
          setError(null);
        }
      } catch (error) {
        if (!controller.signal.aborted)
          setError(error instanceof Error ? error.message : "本地服务未连接");
      }
      if (!controller.signal.aborted)
        timer = setTimeout(() => {
          void refresh();
        }, 3000);
    }
    void refresh();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [api]);
  const state = health?.model.state ?? "";
  const ready = ["ready", "loaded"].includes(state);
  const failed = Boolean(
    error ||
    health?.model.error ||
    ["error", "failed", "unavailable"].includes(state),
  );
  return (
    <div
      className={`model-health ${ready && !failed ? "is-ready" : ""} ${failed ? "is-error" : ""}`}
      title={
        error ||
        health?.model.error ||
        `${health?.model.model_id ?? "正在读取模型状态"} · ${health?.model.device ?? ""}`
      }
    >
      <span className="status-dot" />
      <span>
        {error
          ? "本地服务未连接"
          : health
            ? stateLabels[state] || `模型：${state}`
            : "正在连接本地服务"}
      </span>
      {health && !error && <small>{health.model.device.toUpperCase()}</small>}
      <CircleHelp size={13} />
    </div>
  );
}
