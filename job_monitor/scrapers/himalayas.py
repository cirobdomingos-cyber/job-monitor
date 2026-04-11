from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from job_monitor.core.models import Job
from job_monitor.scrapers.base import BaseScraper
from job_monitor.config import TITLE_KEYWORDS

logger = logging.getLogger(__name__)

BASE_URL = "https://himalayas.app/jobs/api"
SEARCH_URL = "https://himalayas.app/jobs/api/search"


class HimalayasScraper(BaseScraper):
    source = "himalayas"
    rate_limit_delay = 1.5

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []

        # One search request per title keyword keeps us well within the daily limit
        seen_urls: set[str] = set()
        for keyword in TITLE_KEYWORDS:
            try:
                resp = self.get(SEARCH_URL, params={"q": keyword, "limit": 20})
                data = resp.json()
                for raw in data.get("jobs", []):
                    job = self._parse(raw)
                    if job and job.url not in seen_urls:
                        jobs.append(job)
                        seen_urls.add(job.url)
            except Exception as exc:
                logger.exception(f"[{self.source}] Error fetching keyword '{keyword}': {exc}")

        logger.info(f"[{self.source}] Fetched {len(jobs)} jobs")
        return jobs

    # ------------------------------------------------------------------

    def _parse(self, raw: dict[str, Any]) -> Job | None:
        try:
            return Job(
                url=raw.get("url") or f"https://himalayas.app/jobs/{raw.get('slug', '')}",
                title=raw.get("title", ""),
                company=raw.get("company", {}).get("name", "") if isinstance(raw.get("company"), dict) else raw.get("company", ""),
                source=self.source,
                location=raw.get("locationRestrictions") or raw.get("location") or "Remote",
                description=raw.get("description") or raw.get("descriptionTeaser", ""),
                salary=self._salary(raw),
                tags=raw.get("categories", []) + raw.get("jobType", []),
                posted_at=self._parse_date(raw.get("createdAt")),
            )
        except Exception as exc:
            logger.warning(f"[{self.source}] Parse error: {exc} — raw keys: {list(raw.keys())}")
            return None

    @staticmethod
    def _salary(raw: dict) -> str | None:
        lo = raw.get("salaryMin")
        hi = raw.get("salaryMax")
        currency = raw.get("salaryCurrency", "USD")
        if lo and hi:
            return f"{currency} {lo:,}–{hi:,}"
        if lo:
            return f"{currency} {lo:,}+"
        return None

    @staticmethod
    def _parse_date(value) -> datetime | None:
        if not value:
            return None
        try:
            # Himalayas returns ISO strings or timestamps
            if isinstance(value, (int, float)):
                return datetime.utcfromtimestamp(value / 1000)
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
