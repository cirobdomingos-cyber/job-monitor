from __future__ import annotations

import hashlib

from job_monitor.core.models import Job
from job_monitor.storage.db import get_seen_urls, mark_seen


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def filter_new(jobs: list[Job]) -> list[Job]:
    """
    Return only jobs whose URL hash has not been seen before.
    New jobs are immediately marked as seen so a second call in the
    same run won't re-admit them.
    """
    seen = get_seen_urls()
    new_jobs: list[Job] = []

    for job in jobs:
        h = _url_hash(job.url)
        if h not in seen:
            new_jobs.append(job)
            mark_seen(h, job.url, job.source)
            seen.add(h)  # prevent duplicates within the same batch

    return new_jobs
