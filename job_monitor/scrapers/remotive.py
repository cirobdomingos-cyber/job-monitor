from __future__ import annotations

from datetime import datetime
from typing import Any

from job_monitor.core.models import Job
from job_monitor.scrapers.base import BaseScraper

BASE_URL = "https://remotive.com/api/remote-jobs"

# Categories most likely to surface relevant roles
# Full list: https://github.com/remotive-com/remote-jobs-api
TARGET_CATEGORIES = [
    "data",
    "software-dev",
    "product",
]


class RemotiveScraper(BaseScraper):
    source = "remotive"
    rate_limit_delay = 2.0  # max 4 requests/day; we're well under

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen_urls: set[str] = set()

        for category in TARGET_CATEGORIES:
            try:
                resp = self.get(BASE_URL, params={"category": category, "limit": 100})
                data = resp.json()
                for raw in data.get("jobs", []):
                    job = self._parse(raw)
                    if job and job.url not in seen_urls:
                        jobs.append(job)
                        seen_urls.add(job.url)
            except Exception as exc:
                print(f"[{self.source}] Error fetching category '{category}': {exc}")

        print(f"[{self.source}] Fetched {len(jobs)} jobs")
        return jobs

    # ------------------------------------------------------------------

    def _parse(self, raw: dict[str, Any]) -> Job | None:
        try:
            return Job(
                url=raw.get("url", ""),
                title=raw.get("title", ""),
                company=raw.get("company_name", ""),
                source=self.source,
                location=raw.get("candidate_required_location") or "Remote",
                description=raw.get("description", ""),
                salary=raw.get("salary") or None,
                tags=raw.get("tags", []),
                posted_at=self._parse_date(raw.get("publication_date")),
            )
        except Exception as exc:
            print(f"[{self.source}] Parse error: {exc}")
            return None

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
