from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from job_monitor.core.models import Job
from job_monitor.scrapers.base import BaseScraper

# Public API — no auth, no rate limit specified, but be polite
API_URL = "https://remoteok.io/api"


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


class RemoteOkScraper(BaseScraper):
    source = "remoteok"
    rate_limit_delay = 2.0

    def fetch(self) -> list[Job]:
        try:
            # The API returns a metadata dict as the first element — skip it
            resp = self.get(API_URL, params={"tags": "data"})
            raw_list = resp.json()
            if isinstance(raw_list, list) and raw_list:
                raw_list = [r for r in raw_list if isinstance(r, dict) and r.get("id")]
        except Exception as exc:
            print(f"[{self.source}] Fetch error: {exc}")
            return []

        jobs = []
        seen: set[str] = set()
        for raw in raw_list:
            job = self._parse(raw)
            if job and job.url not in seen:
                jobs.append(job)
                seen.add(job.url)

        print(f"[{self.source}] Fetched {len(jobs)} jobs")
        return jobs

    def _parse(self, raw: dict[str, Any]) -> Job | None:
        try:
            url = raw.get("url") or f"https://remoteok.io/remote-jobs/{raw.get('id','')}"
            if not url.startswith("http"):
                url = f"https://remoteok.io{url}"

            salary = self._salary(raw)
            tags = raw.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            return Job(
                url=url,
                title=raw.get("position", ""),
                company=raw.get("company", ""),
                source=self.source,
                location=raw.get("location") or "Remote",
                description=_strip_html(raw.get("description", "")),
                salary=salary,
                tags=tags,
                posted_at=self._parse_date(raw.get("date") or raw.get("epoch")),
            )
        except Exception as exc:
            print(f"[{self.source}] Parse error: {exc}")
            return None

    @staticmethod
    def _salary(raw: dict) -> str | None:
        lo = raw.get("salary_min") or raw.get("salary")
        hi = raw.get("salary_max")
        if lo and hi and str(lo) != str(hi):
            return f"USD {int(lo):,}–{int(hi):,}"
        if lo:
            return f"USD {int(lo):,}+"
        return None

    @staticmethod
    def _parse_date(value) -> datetime | None:
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                return datetime.utcfromtimestamp(int(value))
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None
