import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { KeyRound, LogOut } from "lucide-react";
import type { WorkbenchApi } from "../api/types";
import { onUnauthorized } from "../core/auth";
import { useI18n } from "../i18n";

type Status = "unknown" | "open" | "required" | "signed-in" | "busy";

/**
 * Sign-in for servers that require `PV3D_API_TOKEN`.
 *
 * Shows nothing when the server is open. When any request answers 401, or the
 * session probe reports a requirement, a compact token form appears. A valid
 * token mints an HttpOnly session cookie, so downloads keep working afterwards.
 */
export function AccessTokenPanel({ api }: { api: WorkbenchApi }) {
  const { t, localize } = useI18n();
  const [status, setStatus] = useState<Status>("unknown");
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void api
      .getSession(controller.signal)
      .then((session) => {
        if (controller.signal.aborted) return;
        setStatus(
          !session.required
            ? "open"
            : session.authenticated
              ? "signed-in"
              : "required",
        );
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus("open");
      });
    return () => controller.abort();
  }, [api]);
  useEffect(
    () =>
      onUnauthorized(() => {
        setStatus((current) => (current === "busy" ? current : "required"));
      }),
    [],
  );
  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = token.trim();
    if (!value) return;
    setStatus("busy");
    setError(null);
    try {
      await api.createSession(value);
      setToken("");
      setStatus("signed-in");
    } catch (failure) {
      setStatus("required");
      setError(
        failure instanceof Error
          ? localize(failure.message)
          : t("请求未完成，请重试。"),
      );
    }
  }
  async function signOut() {
    setStatus("busy");
    try {
      await api.deleteSession();
    } finally {
      setStatus("required");
    }
  }
  if (status === "unknown" || status === "open") return null;
  if (status === "signed-in") {
    return (
      <div className="access-token signed-in">
        <KeyRound size={14} />
        <span>{t("已通过访问令牌登录")}</span>
        <button
          type="button"
          className="text-button"
          onClick={() => void signOut()}
        >
          <LogOut size={13} />
          {t("退出登录")}
        </button>
      </div>
    );
  }
  return (
    <form className="access-token" onSubmit={(event) => void submit(event)}>
      <KeyRound size={14} />
      <label id="access-token-title" htmlFor="access-token-input">
        {t("此服务需要访问令牌")}
      </label>
      <input
        id="access-token-input"
        type="password"
        autoComplete="current-password"
        value={token}
        disabled={status === "busy"}
        onChange={(event) => setToken(event.target.value)}
        placeholder={t("输入 PV3D_API_TOKEN")}
      />
      <button
        type="submit"
        className="button primary small"
        disabled={status === "busy" || !token.trim()}
      >
        {t("登录")}
      </button>
      {error && (
        <span role="alert" className="access-token-error">
          {error}
        </span>
      )}
    </form>
  );
}
