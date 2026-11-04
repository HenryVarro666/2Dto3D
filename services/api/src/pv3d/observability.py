"""Logging configuration, request correlation and response hardening for the local API.

The middleware is plain ASGI so it works for streamed file responses without
buffering them, and it never reads request bodies.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from uuid import uuid4

log = logging.getLogger("pv3d.access")
REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line; extra record attributes become fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    """Configure the root logger once; uvicorn loggers propagate into the same handler."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler()
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%dT%H:%M:%S%z")
        )
    root.addHandler(handler)
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True


class BodyLimitMiddleware:
    """Refuse oversized or length-less uploads before any multipart parsing or spooling."""

    def __init__(self, app, limits: dict[str, int]):
        self.app = app
        self.limits = {path: int(size) for path, size in limits.items()}

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("method") in {"POST", "PUT", "PATCH"}:
            limit = self.limits.get(scope.get("path", ""))
            if limit is not None:
                headers = {key.lower(): value for key, value in scope["headers"]}
                raw = headers.get(b"content-length")
                if raw is None:
                    await _reject(send, 411, "Content-Length is required for uploads.")
                    return
                try:
                    declared = int(raw)
                except ValueError:
                    await _reject(send, 400, "Content-Length must be an integer.")
                    return
                if declared > limit:
                    await _reject(send, 413, "The upload exceeds 20 MB.")
                    return
        await self.app(scope, receive, send)


async def _reject(send, status: int, detail: str) -> None:
    body = json.dumps({"detail": detail}).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("latin-1")),
                (b"connection", b"close"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestContextMiddleware:
    """Attach a request ID, security headers and one access-log line per request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope["headers"]}
        inbound = headers.get("x-request-id", "")
        request_id = inbound if REQUEST_ID.fullmatch(inbound) else uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500
        path = scope.get("path", "")
        is_api = path.startswith("/api/")

        async def send_with_context(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                raw = list(message.get("headers", []))
                raw.append((b"x-request-id", request_id.encode("latin-1")))
                raw.append((b"x-content-type-options", b"nosniff"))
                raw.append((b"referrer-policy", b"same-origin"))
                if is_api:
                    content_type = next(
                        (value for key, value in raw if key.lower() == b"content-type"), b""
                    )
                    if content_type.startswith(b"application/json"):
                        raw.append((b"cache-control", b"no-store"))
                message = {**message, "headers": raw}
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            if is_api:
                log.info(
                    "%s %s %s %.1fms",
                    scope.get("method", ""),
                    path,
                    status_code,
                    (time.perf_counter() - started) * 1000,
                    extra={
                        "request_id": request_id,
                        "method": scope.get("method", ""),
                        "path": path,
                        "status": status_code,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    },
                )
