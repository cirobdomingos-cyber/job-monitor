from __future__ import annotations

import re
from typing import Optional

from job_monitor.core.models import Job
from job_monitor.core.profile import FilterConfig


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def _normalise(text: Optional[str]) -> str:
    """Strip HTML, lowercase, and collapse whitespace for consistent matching."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", _strip_html(text).lower().strip())


def matches_title(job: Job, keywords: list[str]) -> bool:
    """Return True if the job title contains at least one target keyword."""
    title = _normalise(job.title)
    return any(kw in title for kw in keywords)


def title_not_excluded(job: Job, exclusions: list[str]) -> bool:
    """Return False if the title contains a disqualifying term (intern, junior, etc.)."""
    title = _normalise(job.title)
    return not any(ex in title for ex in exclusions)


def matches_keywords(job: Job, keywords: list[str]) -> bool:
    """Return True if the description/tags contain at least one body keyword."""
    haystack = _normalise(f"{job.description or ''} {' '.join(job.tags)}")
    return any(kw in haystack for kw in keywords)


def is_geo_excluded(job: Job, exclusions: list[str]) -> bool:
    """Return True if the job matches a geo-exclusion phrase."""
    haystack = _normalise(f"{job.description or ''} {job.location or ''}")
    return any(phrase in haystack for phrase in exclusions)


def apply(jobs: list[Job], config: FilterConfig) -> list[Job]:
    """
    Filter pipeline (in order of cheapness):
      1. Title must match at least one target role keyword.
      2. Title must NOT contain any exclusion terms (intern, junior, etc.).
      3. Description/tags must contain at least one technical keyword.
      4. Must NOT be geo-excluded (US-only signals).
    """
    results = []
    for job in jobs:
        if not matches_title(job, config.title_keywords):
            continue
        if not title_not_excluded(job, config.title_exclusions):
            continue
        if not matches_keywords(job, config.body_keywords):
            continue
        if is_geo_excluded(job, config.geo_exclusions):
            continue
        results.append(job)
    return results
