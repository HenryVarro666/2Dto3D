"""Environment-driven runtime settings with local-first defaults and explicit validation.

Only the service boundary reads the environment. Everything else receives values
through ``Settings`` so tests and scripts can construct deterministic instances.
"""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LOG_FORMATS = ("text", "json")
DEVICES = ("auto", "cpu", "mps", "cuda")
DEFAULT_MAX_PENDING_JOBS = 8  # Includes the running job; reject rather than grow an unbounded queue.
DEFAULT_MULTIVIEW_TIMEOUT_S = 1800
DEFAULT_REFINE_TIMEOUT_S = 300


class SettingsError(ValueError):
    """A configuration value is missing or invalid; the message names the variable."""


def _int(environ: Mapping[str, str], name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise SettingsError(f"{name} must be an integer, got {raw!r}") from error
    if not minimum <= value <= maximum:
        raise SettingsError(f"{name} must be between {minimum} and {maximum}, got {value}")
    return value


def _choice(environ: Mapping[str, str], name: str, default: str, choices: tuple[str, ...]) -> str:
    value = environ.get(name, default).strip() or default
    normalized = value.upper() if name == "PV3D_LOG_LEVEL" else value.lower()
    if normalized not in choices:
        raise SettingsError(f"{name} must be one of {', '.join(choices)}, got {value!r}")
    return normalized


def _origins(environ: Mapping[str, str]) -> tuple[str, ...]:
    raw = environ.get("PV3D_CORS_ORIGINS", "")
    origins = tuple(dict.fromkeys(item.strip() for item in raw.split(",") if item.strip()))
    for origin in origins:
        if origin != "*" and not origin.startswith(("http://", "https://")):
            raise SettingsError(f"PV3D_CORS_ORIGINS entries must be http(s) origins, got {origin!r}")
    return origins


def is_loopback(host: str) -> bool:
    if host in {"localhost", ""}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    log_format: str = "text"
    cors_origins: tuple[str, ...] = ()
    data_dir: Path = field(default_factory=lambda: ROOT / "data" / "runtime")
    model_dir: Path = field(default_factory=lambda: ROOT / "models" / "huggingface")
    device: str = "auto"
    max_pending_jobs: int = DEFAULT_MAX_PENDING_JOBS
    multiview_timeout_s: int = DEFAULT_MULTIVIEW_TIMEOUT_S
    refine_timeout_s: int = DEFAULT_REFINE_TIMEOUT_S

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        environ = os.environ if environ is None else environ
        host = environ.get("PV3D_HOST", "127.0.0.1").strip() or "127.0.0.1"
        return cls(
            host=host,
            port=_int(environ, "PV3D_PORT", 8000, minimum=1, maximum=65535),
            log_level=_choice(environ, "PV3D_LOG_LEVEL", "INFO", LOG_LEVELS),
            log_format=_choice(environ, "PV3D_LOG_FORMAT", "text", LOG_FORMATS),
            cors_origins=_origins(environ),
            data_dir=Path(environ.get("PV3D_DATA_DIR") or ROOT / "data" / "runtime").expanduser().resolve(),
            model_dir=Path(environ.get("PV3D_MODEL_DIR") or ROOT / "models" / "huggingface").expanduser(),
            device=_choice(environ, "PV3D_DEVICE", "auto", DEVICES),
            max_pending_jobs=_int(environ, "PV3D_MAX_PENDING_JOBS", DEFAULT_MAX_PENDING_JOBS, minimum=1, maximum=64),
            multiview_timeout_s=_int(
                environ, "PV3D_MULTIVIEW_TIMEOUT_S", DEFAULT_MULTIVIEW_TIMEOUT_S, minimum=60, maximum=86_400
            ),
            refine_timeout_s=_int(
                environ, "PV3D_REFINE_TIMEOUT_S", DEFAULT_REFINE_TIMEOUT_S, minimum=1, maximum=86_400
            ),
        )

    @property
    def exposes_network(self) -> bool:
        """True when the bind address accepts connections from other hosts."""
        return not is_loopback(self.host)
