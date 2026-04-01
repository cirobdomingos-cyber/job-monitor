from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from job_monitor.core.models import Job

# Default DB path — can be overridden via env var DB_PATH
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    """Create tables if they don't exist."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT    NOT NULL UNIQUE,
                url_hash    TEXT    NOT NULL UNIQUE,
                title       TEXT    NOT NULL,
                company     TEXT    NOT NULL,
                source      TEXT    NOT NULL,
                location    TEXT,
                description TEXT,
                salary      TEXT,
                tags        TEXT,
                posted_at   TEXT,
                fetched_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS seen_urls (
                url_hash TEXT PRIMARY KEY,
                url      TEXT NOT NULL,
                source   TEXT NOT NULL,
                seen_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at  TEXT NOT NULL,
                finished_at TEXT,
                total_fetched   INTEGER DEFAULT 0,
                total_filtered  INTEGER DEFAULT 0,
                total_new       INTEGER DEFAULT 0
            );
        """)


# ---------------------------------------------------------------------------
# Seen-URL helpers (used by dedup layer)
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
        )
        for job in jobs
    ]
    with _conn() as con:
        con.executemany(
            """
            INSERT OR IGNORE INTO jobs
              (url, url_hash, title, company, source, location,
               description, salary, tags, posted_at, fetched_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )


def load_jobs(
    source: Optional[str] = None,
    since: Optional[datetime] = None,
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
    query += " ORDER BY fetched_at DESC LIMIT ?"
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


# ---------------------------------------------------------------------------
# Private helper (duplicated here to avoid circular import with dedup)
# ---------------------------------------------------------------------------

def _url_hash(url: str) -> str:
    import hashlib
    return hashlib.sha256(url.encode()).hexdigest()
