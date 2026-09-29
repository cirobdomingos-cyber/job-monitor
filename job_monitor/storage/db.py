from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from job_monitor.core.models import Job

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"


def _read_db_path_from_dotenv() -> str | None:
    dotenv_path = PROJECT_ROOT / ".env"
    if not dotenv_path.exists():
        return None
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "DB_PATH":
            cleaned = value.strip().strip('"').strip("'")
            return cleaned or None
    return None


def _resolve_db_path() -> Path:
    raw_path = os.getenv("DB_PATH") or _read_db_path_from_dotenv()
    if not raw_path:
        return DEFAULT_DB_PATH
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()


DB_PATH = _resolve_db_path()


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    """Create tables and migrate schema if needed."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                url              TEXT    NOT NULL UNIQUE,
                url_hash         TEXT    NOT NULL UNIQUE,
                title            TEXT    NOT NULL,
                company          TEXT    NOT NULL,
                source           TEXT    NOT NULL,
                location         TEXT,
                description      TEXT,
                salary           TEXT,
                tags             TEXT,
                posted_at        TEXT,
                fetched_at       TEXT    NOT NULL,
                score            INTEGER,
                score_breakdown  TEXT
            );

            CREATE TABLE IF NOT EXISTS seen_urls (
                url_hash TEXT PRIMARY KEY,
                url      TEXT NOT NULL,
                source   TEXT NOT NULL,
                seen_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at      TEXT NOT NULL,
                finished_at     TEXT,
                total_fetched   INTEGER DEFAULT 0,
                total_filtered  INTEGER DEFAULT 0,
                total_new       INTEGER DEFAULT 0
            );
        """)

        # Migrate existing DBs that predate the score columns
        existing = {row[1] for row in con.execute("PRAGMA table_info(jobs)")}
        if "score" not in existing:
            con.execute("ALTER TABLE jobs ADD COLUMN score INTEGER")
        if "score_breakdown" not in existing:
            con.execute("ALTER TABLE jobs ADD COLUMN score_breakdown TEXT")


# ---------------------------------------------------------------------------
# Seen-URL helpers
# ---------------------------------------------------------------------------

def get_seen_urls() -> set[str]:
    with _conn() as con:
        rows = con.execute("SELECT url_hash FROM seen_urls").fetchall()
    return {r["url_hash"] for r in rows}


def mark_seen(url_hash: str, url: str, source: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO seen_urls (url_hash, url, source, seen_at) VALUES (?,?,?,?)",
            (url_hash, url, source, datetime.utcnow().isoformat()),
        )


# ---------------------------------------------------------------------------
# Job persistence
# ---------------------------------------------------------------------------

def save_jobs(jobs: list[Job]) -> None:
    rows = [
        (
            job.url,
            _url_hash(job.url),
            job.title,
            job.company,
            job.source,
            job.location,
            job.description,
            job.salary,
            json.dumps(job.tags),
            job.posted_at.isoformat() if job.posted_at else None,
            job.fetched_at.isoformat(),
            job.score,
            job.score_breakdown,
        )
        for job in jobs
    ]
    with _conn() as con:
        con.executemany(
            """
            INSERT OR IGNORE INTO jobs
              (url, url_hash, title, company, source, location,
               description, salary, tags, posted_at, fetched_at,
               score, score_breakdown)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )


def load_jobs(
    source: Optional[str] = None,
    since: Optional[datetime] = None,
    min_score: Optional[int] = None,
    limit: int = 500,
) -> list[dict]:
    query = "SELECT * FROM jobs WHERE 1=1"
    params: list = []
    if source:
        query += " AND source = ?"
        params.append(source)
    if since:
        query += " AND fetched_at >= ?"
        params.append(since.isoformat())
    if min_score is not None:
        query += " AND (score IS NULL OR score >= ?)"
        params.append(min_score)
    query += " ORDER BY score DESC, fetched_at DESC LIMIT ?"
    params.append(limit)

    with _conn() as con:
        rows = con.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Run tracking
# ---------------------------------------------------------------------------

def start_run() -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO runs (started_at) VALUES (?)",
            (datetime.utcnow().isoformat(),),
        )
        return cur.lastrowid


def finish_run(run_id: int, total_fetched: int, total_filtered: int, total_new: int) -> None:
    with _conn() as con:
        con.execute(
            """UPDATE runs
               SET finished_at=?, total_fetched=?, total_filtered=?, total_new=?
               WHERE id=?""",
            (datetime.utcnow().isoformat(), total_fetched, total_filtered, total_new, run_id),
        )


def _url_hash(url: str) -> str:
    import hashlib
    return hashlib.sha256(url.encode()).hexdigest()
