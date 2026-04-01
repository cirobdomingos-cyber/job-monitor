from __future__ import annotations

import re
from typing import Optional

from job_monitor.core.models import Job
from job_monitor.config import TITLE_KEYWORDS, BODY_KEYWORDS, GEO_EXCLUSIONS


def _normalise(text: Optional[str]) -> str:
    """Lowercase and collapse whitespace for consistent matching."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.lower().strip())


def matches_title(job: Job) -> bool:
    """Return True if the job title contains at least one target keyword."""
    title = _normalise(job.title)
    return any(kw in title for kw in TITLE_KEYWORDS)


def matches_keywords(job: Job) -> bool:
    """Return True if the description/tags contain at least one body keyword."""
    haystack = _normalise(f"{job.description or ''} {' '.join(job.tags)}")
    return any(kw in haystack for kw in BODY_KEYWORDS)


def is_geo_excluded(job: Job) -> bool:
    """Return True if the job appears to be US-only."""
    haystack = _normalise(f"{job.description or ''} {job.location or ''}")
    return any(phrase in haystack for phrase in GEO_EXCLUSIONS)


def apply(jobs: list[Job]) -> list[Job]:
    """
    Filter pipeline:
      1. Title must match at least one target role keyword.
      2. Description/tags must contain at least one technical keyword.
      3. Must NOT be geo-excluded (US-only signals).
    """
    results = []
    for job in jobs:
        if not matches_title(job):
            continue
        if not matches_keywords(job):
            continue
        if is_geo_excluded(job):
            continue
        results.append(job)
    return results
