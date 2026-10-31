"""Start the two local development services and stop only processes we own."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists() or not (ROOT / "apps/web/node_modules").is_dir():
        print("请先在项目根目录运行 make setup。", file=sys.stderr)
        return 1
    processes = []
    stopping = False

    def stop_requested(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop_requested)
    signal.signal(signal.SIGTERM, stop_requested)
    commands = [
        [
            str(python),
            "-m",
            "uvicorn",
            "pv3d.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
            "--reload-dir",
            "services/api/src",
        ],
        [
            "npm",
            "--prefix",
            "apps/web",
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            "5173",
            "--strictPort",
        ],
    ]
    try:
        for command in commands:
            processes.append(subprocess.Popen(command, cwd=ROOT, start_new_session=os.name != "nt"))
        print("\n工作台 http://127.0.0.1:5173  |  API http://127.0.0.1:8000/docs\n", flush=True)
        while not stopping and all(process.poll() is None for process in processes):
            time.sleep(0.2)
        return next((process.returncode for process in processes if process.returncode), 0)
    finally:
        for process in processes:
            if process.poll() is None:
                if os.name == "nt":
                    process.terminate()
                else:
                    os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)


if __name__ == "__main__":
    raise SystemExit(main())
