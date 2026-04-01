from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from job_monitor.core.models import Job
from job_monitor.scrapers.base import BaseScraper

BASE_URL = "https://remote.co"

# Job categories to scrape (server-rendered, no JS needed)
CATEGORY_PATHS = [
    "/remote-jobs/data-science/",
    "/remote-jobs/analyst/",
    "/remote-jobs/software-development/",
    "/remote-jobs/product-manager/",
]


class RemoteCo_Scraper(BaseScraper):
    source = "remoteco"
    rate_limit_delay = 2.0  # polite crawl rate

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen_urls: set[str] = set()

        for path in CATEGORY_PATHS:
            try:
                listing_jobs = self._scrape_listing(path)
                for job in listing_jobs:
                    if job.url not in seen_urls:
                        jobs.append(job)
                        seen_urls.add(job.url)
            except Exception as exc:
                print(f"[{self.source}] Error scraping '{path}': {exc}")

        print(f"[{self.source}] Fetched {len(jobs)} jobs")
        return jobs

    # ------------------------------------------------------------------
    # Listing page → list of Job stubs (no description yet)
    # ------------------------------------------------------------------

    def _scrape_listing(self, path: str) -> list[Job]:
        url = urljoin(BASE_URL, path)
        resp = self.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        jobs: list[Job] = []

        # Each job card lives in a <li class="job_listing"> element
        cards = soup.select("li.job_listing")
        if not cards:
            # Fallback: look for anchor tags with job detail links
            cards = soup.select("a[href*='/remote-jobs/']")

        for card in cards:
            job = self._parse_card(card)
            if job:
                jobs.append(job)

        return jobs

    def _parse_card(self, card) -> Optional[Job]:
        try:
            # Title
            title_el = card.select_one(".position, h3, .job-title, strong")
            title = title_el.get_text(strip=True) if title_el else ""

            # Company
            company_el = card.select_one(".company, .company_name, span.name")
            company = company_el.get_text(strip=True) if company_el else "Unknown"

            # URL
            link_el = card.select_one("a") if card.name != "a" else card
            href = link_el.get("href", "") if link_el else ""
            job_url = urljoin(BASE_URL, href) if href else ""
            if not job_url:
                return None

            # Location tag
            location_el = card.select_one(".location, .job_listing-location")
            location = location_el.get_text(strip=True) if location_el else "Remote"

            # Date
            date_el = card.select_one("time, .date")
            posted_at = None
            if date_el:
                posted_at = self._parse_date(
                    date_el.get("datetime") or date_el.get_text(strip=True)
                )

            # Fetch description from detail page (only if we have a URL)
            description = self._fetch_description(job_url) if job_url else ""

            return Job(
                url=job_url,
                title=title,
                company=company,
                source=self.source,
                location=location,
                description=description,
                posted_at=posted_at,
            )
        except Exception as exc:
            print(f"[{self.source}] Card parse error: {exc}")
            return None

    # ------------------------------------------------------------------
    # Detail page → description text
    # ------------------------------------------------------------------

    def _fetch_description(self, url: str) -> str:
        try:
            resp = self.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            desc_el = soup.select_one(
                ".job_description, .description, article, #job-description"
            )
            if desc_el:
                return desc_el.get_text(separator=" ", strip=True)
            return ""
        except Exception:
            return ""

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y"):
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
