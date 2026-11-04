"""Run the API with validated settings: ``python -m pv3d [--host H] [--port P]``."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import Settings, SettingsError
from .observability import configure_logging
from .store import DataDirectoryLock, LockedDataDirectoryError

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the PV structure workbench API and built web app")
    parser.add_argument("--host", help="Override PV3D_HOST")
    parser.add_argument("--port", type=int, help="Override PV3D_PORT")
    parser.add_argument("--check", action="store_true", help="Validate settings and exit")
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        if args.host is not None or args.port is not None:
            from dataclasses import replace

            settings = replace(
                settings,
                host=args.host if args.host is not None else settings.host,
                port=args.port if args.port is not None else settings.port,
            )
        if not 1 <= settings.port <= 65535:
            raise SettingsError(f"port must be between 1 and 65535, got {settings.port}")
    except SettingsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    configure_logging(settings.log_level, settings.log_format)
    if args.check:
        print(f"settings ok: host={settings.host} port={settings.port} data_dir={settings.data_dir}")
        return 0
    if settings.exposes_network:
        log.warning(
            "Binding to %s exposes an unauthenticated local service; put it behind an authenticating "
            "reverse proxy or keep PV3D_HOST on a loopback address.",
            settings.host,
        )
    try:
        # Fail fast with a readable message; the application lifespan takes the lock for real.
        with DataDirectoryLock(settings.data_dir):
            pass
    except LockedDataDirectoryError as error:
        print(f"error: {error}", file=sys.stderr)
        return 3
    import uvicorn

    from .app import create_app

    uvicorn.run(
        create_app(settings=settings),
        host=settings.host,
        port=settings.port,
        log_config=None,
        access_log=False,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
