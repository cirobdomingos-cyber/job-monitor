"""
scorer.py — Score each job 0–100 based on profile fit.

Dimensions:
  - Title seniority    (0–20)  : Senior/Lead > Mid > Unspecified
  - Tech stack overlap (0–25)  : Count of target stack keywords in description
  - Salary fit         (0–20)  : $80k–$130k target range
  - Location compat    (0–20)  : Worldwide/LATAM-friendly > others
  - Company signals    (0–15)  : Fintech/SaaS/Series B+ language
                       ------
  Total                (0–100)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from job_monitor.core.models import Job

# ---------------------------------------------------------------------------
# Target profile constants
# ---------------------------------------------------------------------------
SALARY_MIN = 80_000
SALARY_MAX = 130_000

SENIORITY_HIGH = ["senior", "lead", "staff", "principal", "head of", "director"]
SENIORITY_MID  = ["mid", "ii", "iii", "2", "3", "specialist", "experienced"]

# Your specific stack — weighted by how central they are to your work
STACK_KEYWORDS: list[tuple[str, int]] = [
    ("python",          3),
    ("sql",             3),
    ("dbt",             3),
    ("databricks",      3),
    ("power bi",        3),
    ("powerbi",         3),
    ("analytics",       2),
    ("data modeling",   2),
    ("data model",      2),
    ("snowflake",       2),
    ("bigquery",        2),
    ("spark",           2),
    ("airflow",         2),
    ("looker",          2),
    ("tableau",         2),
    ("redshift",        1),
    ("metabase",        1),
    ("data warehouse",  1),
    ("data platform",   1),
    ("data pipeline",   1),
    ("aws",             1),
    ("gcp",             1),
    ("azure",           1),
    ("kafka",           1),
    ("pyspark",         2),
    ("mlflow",          1),
    ("streamlit",       2),
    ("fastapi",         2),
]
STACK_MAX_SCORE = 25

# Locations that are Brazil/LATAM-friendly
LATAM_SIGNALS = [
    "worldwide", "anywhere", "global", "latam", "latin america",
    "brazil", "brasil", "argentina", "uruguay", "colombia", "mexico",
    "chile", "peru", "south america",
    " americas",   # space-prefixed to avoid matching "America" or "pan-american"
]
LATAM_REGIONS = [
    "europe", "emea", "apac", "asia", "africa", "oceania",
    "australia", "india", "uk only", "eu only",
]
US_SIGNALS = ["united states", "usa only", "us only", "north america only"]

# Company/sector fit signals
COMPANY_HIGH = [
    "series b", "series c", "series d", "series e",
    "fintech", "saas", "b2b saas", "logistics tech", "logistics",
    "data platform", "data infrastructure", "analytics platform",
    "fully remote", "fully distributed", "remote-first", "distributed team",
]
COMPANY_MID = [
    "startup", "scale-up", "scaleup", "growth stage",
    "series a",
    "financial services", "payments", "insurtech", "proptech",
    "e-commerce", "marketplace",
    "remote",
]


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


def score(job: Job) -> ScoreBreakdown:
    text = _haystack(job)

    seniority = _score_seniority(job.title)
    stack     = _score_stack(text)
    salary    = _score_salary(job.salary)
    location  = _score_location(job.location, text)
    company   = _score_company(text)

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

def _score_seniority(title: str) -> int:
    t = title.lower()
    if any(s in t for s in SENIORITY_HIGH):
        return 20
    if any(s in t for s in SENIORITY_MID):
        return 10
    return 6  # unspecified: give slight benefit of doubt


def _score_stack(text: str) -> int:
    total = 0
    for keyword, weight in STACK_KEYWORDS:
        if keyword in text:
            total += weight
    # Normalize to STACK_MAX_SCORE
    # Max possible raw score if all keywords present ~ 50+; cap at 25
    return min(total, STACK_MAX_SCORE)


def _score_salary(salary_str: Optional[str]) -> int:
    if not salary_str:
        return 8  # unknown — neutral, slight penalty vs confirmed range

    lo, hi = _parse_salary(salary_str)
    if lo is None:
        return 8

    # Convert non-USD rough estimates (GBP/EUR ~1.2x, others ~0.8x)
    currency = _detect_currency(salary_str)
    lo, hi = _to_usd(lo, hi, currency)

    mid = (lo + hi) / 2 if hi else lo

    # Perfect overlap with $80k–$130k
    if SALARY_MIN <= lo and (hi or lo) <= SALARY_MAX:
        return 20
    # Mid point is within range
    if SALARY_MIN <= mid <= SALARY_MAX:
        return 17
    # Overlaps the range
    if lo <= SALARY_MAX and (hi or lo) >= SALARY_MIN:
        return 13
    # Too low
    if (hi or lo) < SALARY_MIN:
        penalty = (SALARY_MIN - (hi or lo)) / SALARY_MIN
        return max(0, int(10 * (1 - penalty)))
    # Too high (overqualified risk, but still worth applying)
    if lo > SALARY_MAX:
        return 12
    return 8


def _score_location(location: Optional[str], text: str) -> int:
    loc = (location or "").lower()
    combined = f"{loc} {text}"

    # Worldwide / LATAM-explicit = best
    if any(s in combined for s in LATAM_SIGNALS):
        return 20
    # Clearly not LATAM-compatible
    if any(s in loc for s in US_SIGNALS):
        return 0
    if any(s in combined for s in LATAM_REGIONS):
        return 8
    # "Remote" with no geo restriction
    if "remote" in loc or "remote" in combined[:200]:
        return 14
    return 6  # unclear


def _score_company(text: str) -> int:
    score = 0
    for signal in COMPANY_HIGH:
        if signal in text:
            score += 3
    for signal in COMPANY_MID:
        if signal in text:
            score += 1
    return min(score, 15)


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
    """Extract low/high salary numbers from a string like 'USD 80,000–120,000'."""
    nums = re.findall(r"[\d,]+(?:\.\d+)?", s.replace(",", ""))
    if not nums:
        return None, None
    floats = [float(n.replace(",", "")) for n in nums]
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
