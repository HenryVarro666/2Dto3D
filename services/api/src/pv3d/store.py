"""Small durable SQLite ledger. Each operation owns its connection across threads."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO
from uuid import uuid4

SCHEMA_VERSION = 1


class SchemaError(RuntimeError):
    """The on-disk ledger was written by a newer build than this one."""


class LockedDataDirectoryError(RuntimeError):
    """Another live server already owns this data directory."""


class DataDirectoryLock:
    """Exclusive advisory lock so two servers never mark each other's jobs interrupted.

    Uses ``fcntl.flock`` where available (Linux, macOS). The lock is released by the
    kernel if the process dies, so a crash never leaves a stale lock behind.
    """

    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "server.lock"
        self._handle: TextIO | None = None

    def acquire(self) -> None:
        try:
            import fcntl
        except ImportError:  # pragma: no cover - Windows has no advisory file locks here.
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.seek(0)
            owner = handle.read().strip() or "another process"
            handle.close()
            raise LockedDataDirectoryError(
                f"{self.path.parent} is already served by {owner}. Stop it or use a different PV3D_DATA_DIR."
            ) from error
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid {os.getpid()}\n")
        handle.flush()
        self._handle = handle

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_exc):
        self.release()


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "assets").mkdir(exist_ok=True)
        (data_dir / "jobs").mkdir(exist_ok=True)
        (data_dir / "refinements").mkdir(exist_ok=True)
        (data_dir / "multiview").mkdir(exist_ok=True)
        self.database = data_dir / "state.sqlite3"
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            stored = connection.execute("PRAGMA user_version").fetchone()[0]
            if stored > SCHEMA_VERSION:
                raise SchemaError(
                    f"{self.database} uses ledger schema {stored}; this build supports up to {SCHEMA_VERSION}."
                )
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY, width INTEGER NOT NULL, height INTEGER NOT NULL,
                    sha256 TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
                    status TEXT NOT NULL, stage TEXT NOT NULL, created_at TEXT NOT NULL,
                    elapsed_ms REAL NOT NULL DEFAULT 0, error TEXT, result_json TEXT
                );
                CREATE TABLE IF NOT EXISTS refinements (
                    id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS captures (
                    id TEXT PRIMARY KEY, asset_ids_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS measurement_records (
                    id TEXT PRIMARY KEY, job_id TEXT NOT NULL, kind TEXT NOT NULL, payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS measurement_job ON measurement_records(job_id);
                CREATE TABLE IF NOT EXISTS multiview_jobs (
                    id TEXT PRIMARY KEY, capture_id TEXT NOT NULL REFERENCES captures(id),
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_asset ON jobs(asset_id);
                CREATE INDEX IF NOT EXISTS refinements_asset ON refinements(asset_id);
                CREATE INDEX IF NOT EXISTS multiview_jobs_capture ON multiview_jobs(capture_id);
            """)
            if stored < SCHEMA_VERSION:
                connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    @property
    def schema_version(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        # WAL + NORMAL keeps every committed transaction consistent after a crash; a
        # power loss may only drop the last few transactions, which the restart marks interrupted.
        connection.execute("PRAGMA synchronous=NORMAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def interrupt_unfinished(self):
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status='interrupted', stage='interrupted', error=?, result_json=NULL "
                "WHERE status IN ('queued','running')",
                ("The server stopped before this task finished. Start a new task to try again.",),
            )
            for row in connection.execute("SELECT id,payload_json FROM multiview_jobs").fetchall():
                job = json.loads(row["payload_json"])
                if job["status"] in {"queued", "running"}:
                    job.update(
                        status="interrupted",
                        stage="interrupted",
                        result=None,
                        error="The server stopped before this task finished. Start a new task to try again.",
                    )
                    connection.execute(
                        "UPDATE multiview_jobs SET payload_json=? WHERE id=?",
                        (json.dumps(job, allow_nan=False), job["id"]),
                    )

    def create_capture(self, asset_ids):
        identifier, created_at = uuid4().hex, datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO captures VALUES (?,?,?)", (identifier, json.dumps(asset_ids), created_at)
            )
        return self.get_capture(identifier)

    def get_capture(self, identifier):
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM captures WHERE id=?", (identifier,)).fetchone()
        if row is None:
            return None
        return {
            "id": identifier,
            "created_at": row["created_at"],
            "assets": [self.get_asset(asset_id) for asset_id in json.loads(row["asset_ids_json"])],
        }

    def create_multiview_job(self, capture_id, total_views):
        job = {
            "id": uuid4().hex,
            "capture_id": capture_id,
            "status": "queued",
            "stage": "queued",
            "view_index": 0,
            "total_views": total_views,
            "created_at": datetime.now(UTC).isoformat(),
            "elapsed_ms": 0.0,
            "error": None,
            "result": None,
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO multiview_jobs VALUES (?,?,?)",
                (job["id"], capture_id, json.dumps(job, allow_nan=False)),
            )
        return job

    def get_multiview_job(self, identifier):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM multiview_jobs WHERE id=?", (identifier,)
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def update_multiview_job(self, identifier, **changes):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM multiview_jobs WHERE id=?", (identifier,)
            ).fetchone()
            job = json.loads(row["payload_json"])
            job.update(changes)
            connection.execute(
                "UPDATE multiview_jobs SET payload_json=? WHERE id=?",
                (json.dumps(job, allow_nan=False), identifier),
            )

    def add_asset(self, asset):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO assets (id,width,height,sha256) VALUES (?,?,?,?)",
                (asset["id"], asset["width"], asset["height"], asset["sha256"]),
            )

    def get_asset(self, identifier):
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM assets WHERE id=?", (identifier,)).fetchone()
        return {**dict(row), "image_url": f"/api/assets/{identifier}/image"} if row else None

    def add_refinement(self, result):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO refinements (id,asset_id,payload_json) VALUES (?,?,?)",
                (result["id"], result["asset_id"], json.dumps(result, allow_nan=False)),
            )

    def get_refinement(self, identifier):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM refinements WHERE id=?", (identifier,)
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def create_job(self, asset_id):
        job = {
            "id": uuid4().hex,
            "asset_id": asset_id,
            "status": "queued",
            "stage": "queued",
            "created_at": datetime.now(UTC).isoformat(),
            "elapsed_ms": 0.0,
            "error": None,
            "result": None,
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO jobs (id,asset_id,status,stage,created_at) VALUES (?,?,?,?,?)",
                tuple(job[key] for key in ("id", "asset_id", "status", "stage", "created_at")),
            )
        return job

    def get_job(self, identifier):
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
        if row is None:
            return None
        job = dict(row)
        result_json = job.pop("result_json")
        job["result"] = json.loads(result_json) if result_json is not None else None
        return job

    def update_job(self, identifier, *, status, stage, elapsed_ms, error=None, result=None):
        serialized = json.dumps(result, allow_nan=False) if result is not None else None
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status=?,stage=?,elapsed_ms=?,error=?,result_json=? WHERE id=?",
                (status, stage, elapsed_ms, error, serialized, identifier),
            )

    def add_measurement_record(self, job_id, kind, record):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO measurement_records VALUES (?,?,?,?)",
                (record["id"], job_id, kind, json.dumps(record, allow_nan=False)),
            )

    def get_measurement_records(self, job_id):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT kind,payload_json FROM measurement_records WHERE job_id=? ORDER BY rowid", (job_id,)
            ).fetchall()
        return [(row["kind"], json.loads(row["payload_json"])) for row in rows]
