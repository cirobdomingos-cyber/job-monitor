#!/usr/bin/env python3
"""
runner.py — Main entry point for the job monitor.

Usage:
    python runner.py               # run all enabled scrapers
    python runner.py --source himalayas remotive   # run specific scrapers
    python runner.py --dry-run     # fetch + filter but don't persist
"""
from __future__ import annotations

import argparse
import logging
import sys
import textwrap
from datetime import datetime

from job_monitor.logging_config import setup_logging
from job_monitor.config import ENABLED_SCRAPERS
from job_monitor.core import dedup, filters
from job_monitor.core.models import Job
from job_monitor.scrapers.himalayas import HimalayasScraper
from job_monitor.scrapers.remotive import RemotiveScraper
from job_monitor.scrapers.weworkremotely import WeWorkRemotelyScraper
from job_monitor.scrapers.remoteco import RemoteCo_Scraper
from job_monitor.storage import db

logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    "himalayas": HimalayasScraper,
    "remotive": RemotiveScraper,
    "weworkremotely": WeWorkRemotelyScraper,
    "remoteco": RemoteCo_Scraper,
}


def run(sources: list[str] | None = None, dry_run: bool = False) -> None:
    db.init_db()
    run_id = db.start_run() if not dry_run else None

    active_sources = sources or [s for s, enabled in ENABLED_SCRAPERS.items() if enabled]

    all_fetched: list[Job] = []
    for source in active_sources:
        if source not in SCRAPER_MAP:
            logger.warning(f"Unknown source '{source}' — skipping")
            continue
        scraper_cls = SCRAPER_MAP[source]
        logger.info(f"{'─'*50}")
        logger.info(f"Running scraper: {source}")
        logger.info(f"{'─'*50}")
        try:
            jobs = scraper_cls().fetch()
            all_fetched.extend(jobs)
        except Exception as exc:
            logger.exception(f"Scraper '{source}' failed: {exc}")

    total_fetched = len(all_fetched)
    logger.info(f"Total fetched:   {total_fetched}")

    # --- Filter ---
    filtered = filters.apply(all_fetched)
    total_filtered = len(filtered)
    logger.info(f"After filtering: {total_filtered}")

    # --- Dedup ---
    if dry_run:
        new_jobs = filtered  # skip DB check in dry-run mode
    else:
        new_jobs = dedup.filter_new(filtered)

    total_new = len(new_jobs)
    logger.info(f"New (unseen):    {total_new}")

    # --- Persist ---
    if not dry_run and new_jobs:
        db.save_jobs(new_jobs)
        db.finish_run(run_id, total_fetched, total_filtered, total_new)

    # --- Print results ---
    _print_results(new_jobs, dry_run)


def _print_results(jobs: list[Job], dry_run: bool) -> None:
    if not jobs:
        logger.info("No new jobs this run.")
        return

    label = "[DRY RUN] " if dry_run else ""
    logger.info(f"{'═'*60}")
    logger.info(f"  {label}{len(jobs)} new job(s) found — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"{'═'*60}")

    for i, job in enumerate(jobs, 1):
        salary_str = f"  💰 {job.salary}" if job.salary else ""
        location_str = f"  📍 {job.location}" if job.location else ""
        tags_str = f"  🏷  {', '.join(job.tags[:5])}" if job.tags else ""
        desc_preview = ""
        if job.description:
            clean = " ".join(job.description.split())
            desc_preview = f"\n     {textwrap.shorten(clean, width=120, placeholder='…')}"

        logger.info(
            f"  [{i:02d}] {job.title}\n"
            f"       {job.company}{location_str}{salary_str}\n"
            f"       🔗 {job.url}{tags_str}{desc_preview}"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Job monitor runner")
    parser.add_argument(
        "--source",
        nargs="+",
        choices=list(SCRAPER_MAP.keys()),
        help="Run only these scrapers (default: all enabled)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and filter but do not write to DB",
    )
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = _parse_args()
    run(sources=args.source, dry_run=args.dry_run)
