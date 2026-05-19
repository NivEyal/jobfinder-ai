import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from src.job import Job


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    fingerprint TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_job_id TEXT NOT NULL,
    canonical_url TEXT,
    company TEXT,
    title TEXT,
    location TEXT,
    region TEXT,
    remote_type TEXT,
    employment_type TEXT,
    seniority TEXT,
    years_experience REAL,
    salary_min INTEGER,
    salary_max INTEGER,
    language TEXT,
    apply_email TEXT,
    apply_url TEXT,
    status TEXT,
    first_seen_at TEXT,
    last_seen_at TEXT,
    raw_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source, source_job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(fingerprint);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen ON jobs(last_seen_at);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_fingerprint TEXT NOT NULL,
    source TEXT,
    source_job_id TEXT,
    method TEXT NOT NULL,
    status TEXT NOT NULL,
    dry_run INTEGER NOT NULL,
    target TEXT,
    detail TEXT,
    match_score INTEGER,
    match_verdict TEXT,
    created_at TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    UNIQUE(job_fingerprint, method, dry_run)
);

CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_fingerprint);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    query TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    jobs_found INTEGER DEFAULT 0,
    jobs_saved INTEGER DEFAULT 0,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    source TEXT,
    query TEXT,
    error_type TEXT,
    error_message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS application_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_fingerprint TEXT,
    source TEXT,
    source_job_id TEXT,
    level TEXT NOT NULL,
    event TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS source_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    snapshot_type TEXT NOT NULL,
    url TEXT,
    captured_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    checksum TEXT
);
"""


class SQLiteStore:
    """SQLite persistence for jobs, applications, runs, errors, logs, and snapshots."""

    def __init__(self, db_path: str | Path = "data_folder/output/jobs_storage.sqlite3"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save_job(self, job: Job) -> str:
        data = job.to_dict()
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    fingerprint, source, source_job_id, canonical_url, company, title, location, region,
                    remote_type, employment_type, seniority, years_experience, salary_min, salary_max,
                    language, apply_email, apply_url, status, first_seen_at, last_seen_at, raw_json, updated_at
                )
                VALUES (
                    :fingerprint, :source, :source_job_id, :canonical_url, :company, :title, :location, :region,
                    :remote_type, :employment_type, :seniority, :years_experience, :salary_min, :salary_max,
                    :language, :apply_email, :apply_url, :status, :first_seen_at, :last_seen_at, :raw_json, :updated_at
                )
                ON CONFLICT(fingerprint) DO UPDATE SET
                    last_seen_at=excluded.last_seen_at,
                    status=excluded.status,
                    raw_json=excluded.raw_json,
                    updated_at=excluded.updated_at
                """,
                {
                    **data,
                    "raw_json": json.dumps(data, ensure_ascii=False),
                    "updated_at": now,
                },
            )
        return job.fingerprint

    def record_application(self, result: Any, match_result: Any | None = None):
        data = result.to_dict()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO applications (
                    job_fingerprint, source, source_job_id, method, status, dry_run, target, detail,
                    match_score, match_verdict, created_at, raw_json
                )
                VALUES (
                    :job_fingerprint, :source, :source_job_id, :method, :status, :dry_run, :target, :detail,
                    :match_score, :match_verdict, :created_at, :raw_json
                )
                """,
                {
                    "job_fingerprint": result.job_fingerprint,
                    "source": result.source,
                    "source_job_id": result.source_job_id,
                    "method": result.method,
                    "status": result.status,
                    "dry_run": 1 if result.dry_run else 0,
                    "target": result.target,
                    "detail": result.detail,
                    "match_score": getattr(match_result, "score", None),
                    "match_verdict": getattr(match_result, "verdict", None),
                    "created_at": data["created_at"],
                    "raw_json": json.dumps(data, ensure_ascii=False),
                },
            )

    def has_application(self, job_fingerprint: str, include_dry_run: bool = True) -> bool:
        sql = "SELECT 1 FROM applications WHERE job_fingerprint = ?"
        params: tuple[Any, ...] = (job_fingerprint,)
        if not include_dry_run:
            sql += " AND dry_run = 0"
        sql += " LIMIT 1"
        with self.connect() as conn:
            return conn.execute(sql, params).fetchone() is not None

    def start_ingestion_run(self, source: str, query: Dict[str, Any]) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ingestion_runs (source, query, status, started_at, raw_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source, json.dumps(query, ensure_ascii=False), "running", utc_now(), json.dumps(query, ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

    def finish_ingestion_run(self, run_id: int, status: str, jobs_found: int, jobs_saved: int):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE ingestion_runs
                SET status = ?, finished_at = ?, jobs_found = ?, jobs_saved = ?
                WHERE id = ?
                """,
                (status, utc_now(), jobs_found, jobs_saved, run_id),
            )

    def record_ingestion_error(
        self,
        source: str,
        query: Dict[str, Any],
        error: Exception | str,
        run_id: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        error_type = type(error).__name__ if isinstance(error, Exception) else "Error"
        error_message = str(error)
        raw = {"source": source, "query": query, "error": error_message, "extra": extra or {}}
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_errors (run_id, source, query, error_type, error_message, created_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    source,
                    json.dumps(query, ensure_ascii=False),
                    error_type,
                    error_message,
                    utc_now(),
                    json.dumps(raw, ensure_ascii=False),
                ),
            )

    def log_application(
        self,
        event: str,
        message: str,
        result: Any | None = None,
        level: str = "info",
        extra: Optional[Dict[str, Any]] = None,
    ):
        raw = {"event": event, "message": message, "extra": extra or {}}
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO application_logs (
                    job_fingerprint, source, source_job_id, level, event, message, created_at, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    getattr(result, "job_fingerprint", None),
                    getattr(result, "source", None),
                    getattr(result, "source_job_id", None),
                    level,
                    event,
                    message,
                    utc_now(),
                    json.dumps(raw, ensure_ascii=False),
                ),
            )

    def save_source_snapshot(self, source: str, snapshot_type: str, payload: str, url: str = ""):
        import hashlib

        checksum = hashlib.sha256((payload or "").encode("utf-8")).hexdigest()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO source_snapshots (source, snapshot_type, url, captured_at, payload, checksum)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source, snapshot_type, url, utc_now(), payload, checksum),
            )

    def table_counts(self) -> Dict[str, int]:
        tables = [
            "jobs",
            "applications",
            "ingestion_runs",
            "ingestion_errors",
            "application_logs",
            "source_snapshots",
        ]
        with self.connect() as conn:
            return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}

    def list_applications(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM applications ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]

    def save_jobs(self, jobs: Iterable[Job]) -> int:
        now = utc_now()
        rows = []
        for job in jobs:
            data = job.to_dict()
            rows.append({
                **data,
                "raw_json": json.dumps(data, ensure_ascii=False),
                "updated_at": now,
            })
        if not rows:
            return 0
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO jobs (
                    fingerprint, source, source_job_id, canonical_url, company, title, location, region,
                    remote_type, employment_type, seniority, years_experience, salary_min, salary_max,
                    language, apply_email, apply_url, status, first_seen_at, last_seen_at, raw_json, updated_at
                )
                VALUES (
                    :fingerprint, :source, :source_job_id, :canonical_url, :company, :title, :location, :region,
                    :remote_type, :employment_type, :seniority, :years_experience, :salary_min, :salary_max,
                    :language, :apply_email, :apply_url, :status, :first_seen_at, :last_seen_at, :raw_json, :updated_at
                )
                ON CONFLICT(fingerprint) DO UPDATE SET
                    last_seen_at=excluded.last_seen_at,
                    status=excluded.status,
                    raw_json=excluded.raw_json,
                    updated_at=excluded.updated_at
                """,
                rows,
            )
        return len(rows)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
