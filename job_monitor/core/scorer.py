"""
scorer.py — Score each job 0–100 based on profile fit.

Dimensions:
  - Title seniority    (0–20)  : Senior/Lead > Mid > Unspecified
  - Tech stack overlap (0–25)  : Count of target stack keywords in description
  - Salary fit         (0–20)  : Configurable target range
  - Location compat    (0–20)  : Preferred locations > others
  - Company signals    (0–15)  : Configurable sector/stage keywords
                       ------
  Total                (0–100)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from job_monitor.core.models import Job
from job_monitor.core.profile import ScoringConfig


@dataclass
class ScoreBreakdown:
    total: int
    seniority: int
    stack: int
    salary: int
    location: int
    company: int

    def label(self) -> str:
        if self.total >= 80:
            return "Strong match"
        if self.total >= 60:
            return "Good match"
        if self.total >= 40:
            return "Possible"
        return "Weak"


def score(job: Job, config: ScoringConfig) -> ScoreBreakdown:
    text = _haystack(job)

    seniority = _score_seniority(job.title, config)
    stack     = _score_stack(text, config)
    salary    = _score_salary(job.salary, config)
    location  = _score_location(job.location, text, config)
    company   = _score_company(text, config)

    total = seniority + stack + salary + location + company
    return ScoreBreakdown(
        total=min(total, 100),
        seniority=seniority,
        stack=stack,
        salary=salary,
        location=location,
        company=company,
    )


# ---------------------------------------------------------------------------
# Individual dimension scorers
# ---------------------------------------------------------------------------

def _score_seniority(title: str, config: ScoringConfig) -> int:
    t = title.lower()
    if any(s in t for s in config.seniority_high):
        return 20
    if any(s in t for s in config.seniority_mid):
        return 10
    return 6  # unspecified: give slight benefit of doubt


def _score_stack(text: str, config: ScoringConfig) -> int:
    total = 0
    for keyword, weight in config.stack_keywords.items():
        if keyword in text:
            total += weight
    return min(total, config.stack_max_score)


def _score_salary(salary_str: Optional[str], config: ScoringConfig) -> int:
    if not salary_str:
        return 8  # unknown — neutral, slight penalty vs confirmed range

    lo, hi = _parse_salary(salary_str)
    if lo is None:
        return 8

    currency = _detect_currency(salary_str)
    lo, hi = _to_usd(lo, hi, currency)

    mid = (lo + hi) / 2 if hi else lo

    sal_min = config.salary_min
    sal_max = config.salary_max

    # Perfect overlap with target range
    if sal_min <= lo and (hi or lo) <= sal_max:
        return 20
    # Mid point is within range
    if sal_min <= mid <= sal_max:
        return 17
    # Overlaps the range
    if lo <= sal_max and (hi or lo) >= sal_min:
        return 13
    # Too low
    if (hi or lo) < sal_min:
        penalty = (sal_min - (hi or lo)) / sal_min
        return max(0, int(10 * (1 - penalty)))
    # Too high (overqualified risk, but still worth applying)
    if lo > sal_max:
        return 12
    return 8


def _score_location(location: Optional[str], text: str, config: ScoringConfig) -> int:
    loc = (location or "").lower()
    combined = f"{loc} {text}"

    # Preferred locations = best
    if any(s in combined for s in config.location_preferred):
        return 20
    # Clearly excluded
    if any(s in loc for s in config.location_excluded):
        return 0
    if any(s in combined for s in config.location_neutral_regions):
        return 8
    # "Remote" with no geo restriction
    if "remote" in loc or "remote" in combined[:200]:
        return 14
    return 6  # unclear


def _score_company(text: str, config: ScoringConfig) -> int:
    total = 0
    for signal in config.company_high:
        if signal in text:
            total += 3
    for signal in config.company_mid:
        if signal in text:
            total += 1
    return min(total, 15)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _haystack(job: Job) -> str:
    parts = [
        job.title or "",
        job.company or "",
        job.description or "",
        job.location or "",
        " ".join(job.tags),
    ]
    return " ".join(parts).lower()


def _parse_salary(s: str) -> tuple[Optional[float], Optional[float]]:
    """Extract low/high salary numbers from a string like 'USD 80,000–120,000' or '$120k'."""
    # Match numbers optionally followed by k/K multiplier
    tokens = re.findall(r"[\d,]+(?:\.\d+)?[kK]?", s.replace(",", ""))
    if not tokens:
        return None, None
    floats: list[float] = []
    for tok in tokens:
        if tok.lower().endswith("k"):
            floats.append(float(tok[:-1]) * 1000)
        else:
            floats.append(float(tok))
    # Treat numbers < 1000 as hourly/monthly shortcuts — skip
    floats = [f for f in floats if f >= 1000]
    if not floats:
        return None, None
    lo = floats[0]
    hi = floats[1] if len(floats) > 1 else None
    return lo, hi


def _detect_currency(s: str) -> str:
    s_upper = s.upper()
    for cur in ("GBP", "EUR", "CAD", "AUD", "BRL"):
        if cur in s_upper:
            return cur
    return "USD"


def _to_usd(lo: float, hi: Optional[float], currency: str) -> tuple[float, Optional[float]]:
    rates = {"USD": 1.0, "GBP": 1.27, "EUR": 1.09, "CAD": 0.74, "AUD": 0.66, "BRL": 0.18}
    rate = rates.get(currency, 1.0)
    return lo * rate, (hi * rate if hi else None)
