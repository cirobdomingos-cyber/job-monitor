from __future__ import annotations

import html
import re
import time
from datetime import datetime
from typing import Any

import requests

from job_monitor.core.models import Job
from job_monitor.scrapers.base import BaseScraper

API_BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
JOB_DETAIL_BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"

# Curated list of Series B+ SaaS / Fintech / Logistics companies
# using Greenhouse ATS. Format: (display_name, greenhouse_board_slug)
# To add more: find the slug at https://boards.greenhouse.io/<slug>/jobs
COMPANIES: list[tuple[str, str]] = [
    # --- Fintech ---
    ("Brex", "brex"),
    ("Ramp", "rampnetwork"),
    ("Stripe", "stripe"),
    ("Chime", "chime"),
    ("Mercury", "mercury"),
    ("Navan", "tripactions"),
    ("Remote", "remote"),
    ("Gusto", "gusto"),
    ("Carta", "carta"),
    ("Adyen", "adyen"),
    # --- SaaS / Data ---
    ("Figma", "figma"),
    ("Vercel", "vercel"),
    ("Airtable", "airtable"),
    ("Fivetran", "fivetran"),
    ("Amplitude", "amplitude"),
    ("Mixpanel", "mixpanel"),
    ("Segment / Twilio", "twilio"),
    ("Hightouch", "hightouch"),
    ("Grafana Labs", "grafanalabs"),
    ("Databricks", "databricks"),
    ("Starburst", "starburst"),
    # --- Logistics / Ops Tech ---
    ("Flexport", "flexport"),
    ("project44", "project44"),
    ("Samsara", "samsara"),
    # --- Health / Other Series B+ ---
    ("Cerebral", "cerebral"),
    ("Calm", "calm"),
]


def _strip_html(text: str) -> str:
    unescaped = html.unescape(text)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescaped)).strip()


class GreenhouseScraper(BaseScraper):
    source = "greenhouse"
    rate_limit_delay = 0.5  # Greenhouse API is fast and permissive

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for company_name, slug in COMPANIES:
            try:
                company_jobs = self._fetch_company(company_name, slug)
                for job in company_jobs:
                    if job.url not in seen:
                        jobs.append(job)
                        seen.add(job.url)
            except Exception as exc:
                # Many slugs may 404 if company changed their board — skip silently
                if "404" not in str(exc) and "Not Found" not in str(exc):
                    print(f"[{self.source}] Error fetching {company_name}: {exc}")

        print(f"[{self.source}] Fetched {len(jobs)} jobs across {len(COMPANIES)} companies")
        return jobs

    def _fetch_company(self, company_name: str, slug: str) -> list[Job]:
        resp = self.session.get(
            API_BASE.format(slug=slug),
            params={"content": "true"},
            timeout=15,
        )
        time.sleep(self.rate_limit_delay)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        raw_jobs = data.get("jobs", [])

        jobs = []
        for raw in raw_jobs:
            job = self._parse(raw, company_name, slug)
            if job:
                jobs.append(job)
        return jobs

    def _parse(self, raw: dict[str, Any], company_name: str, slug: str) -> Job | None:
        try:
            title = raw.get("title", "")

            # Location — Greenhouse stores location as a dict
            loc = raw.get("location", {})
            location = loc.get("name", "Remote") if isinstance(loc, dict) else str(loc or "Remote")

            # Description — included when content=true
            description = _strip_html(raw.get("content", "") or "")

            # Tags from metadata/departments
            tags = []
            for dept in raw.get("departments", []):
                if dept.get("name"):
                    tags.append(dept["name"])
            for office in raw.get("offices", []):
                if office.get("name"):
                    tags.append(office["name"])

            url = raw.get("absolute_url") or f"https://boards.greenhouse.io/{slug}/jobs/{raw.get('id','')}"

            return Job(
                url=url,
                title=title,
                company=company_name,
                source=self.source,
                location=location,
                description=description,
                tags=tags,
                posted_at=self._parse_date(raw.get("updated_at") or raw.get("created_at")),
            )
        except Exception as exc:
            print(f"[{self.source}] Parse error for {company_name}: {exc}")
            return None

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
