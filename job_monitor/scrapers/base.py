from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Optional

import requests

from job_monitor.core.models import Job

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; job-monitor/1.0; "
        "+https://github.com/your-handle/job-monitor)"
    )
}


class BaseScraper(ABC):
    """
    All scrapers inherit from this class and implement `fetch()`.
    HTTP helpers are provided so each scraper doesn't re-implement
    retry / back-off logic.
    """

    source: str  # must be set by subclass
    rate_limit_delay: float = 1.0  # seconds between requests

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @abstractmethod
    def fetch(self) -> list[Job]:
        """Fetch jobs from the source. Returns a list of Job objects."""
        ...

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def get(
        self,
        url: str,
        params: Optional[dict] = None,
        retries: int = 3,
        backoff: float = 2.0,
    ) -> requests.Response:
        for attempt in range(1, retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=15)
                if resp.status_code == 429:
                    wait = backoff * attempt
                    print(f"[{self.source}] Rate limited — waiting {wait}s …")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                time.sleep(self.rate_limit_delay)
                return resp
            except requests.RequestException as exc:
                if attempt == retries:
                    raise
                wait = backoff * attempt
                print(f"[{self.source}] Request error ({exc}) — retry {attempt}/{retries} in {wait}s")
                time.sleep(wait)
        raise RuntimeError(f"[{self.source}] All {retries} retries exhausted for {url}")
