/**
 * Browser-side session state for the optional server access token.
 *
 * The API answers 401 when `PV3D_API_TOKEN` is configured and no bearer header
 * or session cookie accompanies the request. The client reports such failures
 * here so the workbench can show one sign-in panel instead of scattered errors.
 */
export class AuthRequiredError extends Error {
  readonly name = "AuthRequiredError";
  constructor() {
    super("需要访问令牌才能使用本地服务。");
  }
}

type Listener = () => void;
const listeners = new Set<Listener>();

export function onUnauthorized(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function reportUnauthorized(): void {
  for (const listener of listeners) listener();
}

export function isAuthRequired(error: unknown): error is AuthRequiredError {
  return error instanceof Error && error.name === "AuthRequiredError";
}
