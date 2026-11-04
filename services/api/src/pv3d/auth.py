"""Optional shared-token authentication for the local API.

When ``PV3D_API_TOKEN`` is set, every ``/api`` request except the health probe and
the session endpoints must carry the token as ``Authorization: Bearer <token>``
or a session cookie minted by ``POST /api/session``. The cookie holds an HMAC of
the token, never the token itself, and is HttpOnly + SameSite=Strict so that
plain ``<a download>`` links keep working while cross-site requests do not.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from http.cookies import SimpleCookie

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

log = logging.getLogger(__name__)
COOKIE_NAME = "pv3d_session"
OPEN_PATHS = frozenset({"/api/health", "/api/session"})
UNAUTHORIZED = "Authentication required. Send the access token or sign in."


def session_value(token: str) -> str:
    """Cookie payload derived from the token; equal tokens give equal values."""
    return hmac.new(token.encode("utf-8"), b"pv3d-session-v1", hashlib.sha256).hexdigest()


def _constant_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def _cookie_session(headers: dict[str, str]) -> str | None:
    raw = headers.get("cookie")
    if not raw:
        return None
    jar: SimpleCookie = SimpleCookie()
    try:
        jar.load(raw)
    except Exception:  # noqa: BLE001 - a malformed cookie header is simply "no session".
        return None
    morsel = jar.get(COOKIE_NAME)
    return morsel.value if morsel is not None else None


def is_authenticated(headers: dict[str, str], token: str) -> bool:
    authorization = headers.get("authorization", "")
    scheme, _, credential = authorization.partition(" ")
    if scheme.lower() == "bearer" and credential and _constant_equal(credential.strip(), token):
        return True
    session = _cookie_session(headers)
    return session is not None and _constant_equal(session, session_value(token))


class TokenAuthMiddleware:
    """Pure ASGI guard: reject unauthenticated API calls before any route or body parsing."""

    def __init__(self, app, token: str):
        if not token:
            raise ValueError("TokenAuthMiddleware requires a nonempty token")
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path.startswith("/api/") and path not in OPEN_PATHS:
                headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope["headers"]}
                if not is_authenticated(headers, self.token):
                    body = json.dumps({"detail": UNAUTHORIZED}).encode("utf-8")
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 401,
                            "headers": [
                                (b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode("latin-1")),
                                (b"www-authenticate", b'Bearer realm="pv3d"'),
                                (b"cache-control", b"no-store"),
                            ],
                        }
                    )
                    await send({"type": "http.response.body", "body": body})
                    return
        await self.app(scope, receive, send)


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=512)


def register_session_routes(app: FastAPI, token: str, max_age_s: int) -> None:
    """Cookie sessions for the browser UI; API clients can keep using the bearer header."""

    @app.get("/api/session")
    def session_status(request: Request):
        headers = {key.lower(): value for key, value in request.headers.items()}
        return {"required": True, "authenticated": is_authenticated(headers, token)}

    @app.post("/api/session")
    def create_session(body: SessionRequest, request: Request, response: Response):
        if not _constant_equal(body.token, token):
            log.warning("Rejected access token from %s", request.client.host if request.client else "?")
            raise HTTPException(401, "The access token is not valid.")
        secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        response.set_cookie(
            COOKIE_NAME,
            session_value(token),
            max_age=max_age_s,
            httponly=True,
            samesite="strict",
            secure=secure,
            path="/",
        )
        return {"required": True, "authenticated": True}

    @app.delete("/api/session")
    def delete_session(response: Response):
        response.delete_cookie(COOKIE_NAME, path="/")
        return {"required": True, "authenticated": False}
