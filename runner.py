#!/usr/bin/env python3
"""
runner.py — Main entry point for the job monitor.

Usage:
    python runner.py                          # run with default profile
    python runner.py --profile my_search      # run with custom profile
    python runner.py --source himalayas       # run specific scrapers
    python runner.py --dry-run                # fetch + filter, don't persist
"""
from __future__ import annotations

import argparse
import logging
import sys
import textwrap
from datetime import datetime

from job_monitor.logging_config import setup_logging
from job_monitor.core import dedup, filters
from job_monitor.core.models import Job
from job_monitor.core.profile import Profile, load_profile, list_profiles
from job_monitor.core.scorer import score as score_job
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

# Add optional scrapers if available
try:
    from job_monitor.scrapers.remoteok import RemoteOkScraper
    SCRAPER_MAP["remoteok"] = RemoteOkScraper
except ImportError:
    pass

try:
    from job_monitor.scrapers.greenhouse import GreenhouseScraper
    SCRAPER_MAP["greenhouse"] = GreenhouseScraper
except ImportError:
    pass


SCORE_LABELS = {80: "Strong match", 60: "Good match", 40: "Possible", 0: "Weak"}


def run(
    profile: Profile,
    sources: list[str] | None = None,
    dry_run: bool = False,
) -> None:
    logger.info(f"Profile: {profile.name}")

    db.init_db()
    run_id = db.start_run() if not dry_run else None

    # Use profile's scraper toggles, overridden by --source if given
    if sources:
        active_sources = sources
    else:
        active_sources = [
            s for s, enabled in profile.enabled_scrapers.items() if enabled
        ]

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

    # --- Filter (using profile's filter config) ---
    filtered = filters.apply(all_fetched, profile.filters)
    total_filtered = len(filtered)
    logger.info(f"After filtering: {total_filtered}")

    # --- Score (using profile's scoring config) ---
    for job in filtered:
        breakdown = score_job(job, profile.scoring)
        job.score = breakdown.total
        job.score_breakdown = str({
            "seniority": breakdown.seniority,
            "stack": breakdown.stack,
            "salary": breakdown.salary,
            "location": breakdown.location,
            "company": breakdown.company,
        })

    filtered.sort(key=lambda j: j.score or 0, reverse=True)

    # --- Dedup ---
    if dry_run:
        new_jobs = filtered
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
        score_str = ""
        if job.score is not None:
            score_label = next(
                (l for threshold, l in sorted(SCORE_LABELS.items(), reverse=True) if job.score >= threshold),
                "Weak",
            )
            score_str = f" ★ {job.score}/100 ({score_label})"

        salary_str = f"  💰 {job.salary}" if job.salary else ""
        location_str = f"  📍 {job.location}" if job.location else ""
        tags_str = f"  🏷  {', '.join(job.tags[:5])}" if job.tags else ""
        desc_preview = ""
        if job.description:
            clean = " ".join(job.description.split())
            desc_preview = f"\n     {textwrap.shorten(clean, width=120, placeholder='…')}"

        logger.info(
            f"  [{i:02d}]{score_str} {job.title}\n"
            f"       {job.company}{location_str}{salary_str}\n"
            f"       🔗 {job.url}{tags_str}{desc_preview}"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Job monitor runner")
    parser.add_argument(
        "--profile",
        default=None,
        help=(
            "Profile name or path to YAML file "
            f"(available: {', '.join(list_profiles()) or 'none'})"
        ),
    )
    parser.add_argument(
        "--source",
        nargs="+",
        choices=list(SCRAPER_MAP.keys()),
        help="Run only these scrapers (default: all enabled in profile)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and filter but do not write to DB",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Force UTF-8 output on Windows so box-drawing / emoji chars don't crash
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    setup_logging()
    args = _parse_args()
    profile = load_profile(args.profile)
    run(profile=profile, sources=args.source, dry_run=args.dry_run)
