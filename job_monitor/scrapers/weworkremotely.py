from __future__ import annotations

import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from job_monitor.core.models import Job
from job_monitor.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Public RSS feeds — no auth needed, ToS-safe
RSS_FEEDS = {
    "data-science": "https://weworkremotely.com/categories/remote-data-science-jobs.rss",
    "devops-sysadmin": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "product": "https://weworkremotely.com/categories/remote-product-jobs.rss",
    "all-other": "https://weworkremotely.com/categories/remote-all-other-jobs.rss",
}


class WeWorkRemotelyScraper(BaseScraper):
    source = "weworkremotely"
    rate_limit_delay = 1.0

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen_urls: set[str] = set()

        for feed_name, feed_url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                if feed.bozo and not feed.entries:
                    logger.warning(f"[{self.source}] Failed to parse feed '{feed_name}': {feed.bozo_exception}")
                    continue
                for entry in feed.entries:
                    job = self._parse(entry)
                    if job and job.url not in seen_urls:
                        jobs.append(job)
                        seen_urls.add(job.url)
            except Exception as exc:
                logger.exception(f"[{self.source}] Error fetching feed '{feed_name}': {exc}")

        logger.info(f"[{self.source}] Fetched {len(jobs)} jobs")
        return jobs

    # ------------------------------------------------------------------

    def _parse(self, entry) -> Job | None:
        try:
            # WWR encodes "Company: Title" in the title field
            raw_title: str = entry.get("title", "")
            if ": " in raw_title:
                company, title = raw_title.split(": ", 1)
            else:
                title = raw_title
                company = entry.get("author", "Unknown")

            # Region tag sits in the title as "[Region] Company: Title"
            location = "Remote"
            if raw_title.startswith("["):
                region_end = raw_title.find("]")
                if region_end != -1:
                    location = raw_title[1:region_end]
                    rest = raw_title[region_end + 2:].strip()
                    if ": " in rest:
                        company, title = rest.split(": ", 1)
                    else:
                        title = rest

            description = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")

            return Job(
                url=entry.get("link", ""),
                title=title.strip(),
                company=company.strip(),
                source=self.source,
                location=location,
                description=description,
                tags=self._extract_tags(entry),
                posted_at=self._parse_date(entry.get("published")),
            )
        except Exception as exc:
            logger.warning(f"[{self.source}] Parse error: {exc}")
            return None

    @staticmethod
    def _extract_tags(entry) -> list[str]:
        tags = []
        for tag in entry.get("tags", []):
            term = tag.get("term", "")
            if term:
                tags.append(term)
        return tags

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return parsedate_to_datetime(value)
        except Exception:
            try:
                return datetime.fromisoformat(value)
            except Exception:
                return None
