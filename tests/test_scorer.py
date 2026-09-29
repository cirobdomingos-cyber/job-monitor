"""Tests for job_monitor.core.scorer — job fit scoring engine."""
from __future__ import annotations

import pytest

from job_monitor.core.models import Job
from job_monitor.core.profile import ScoringConfig
from job_monitor.core.scorer import (
    ScoreBreakdown,
    _detect_currency,
    _parse_salary,
    _score_company,
    _score_location,
    _score_seniority,
    _score_stack,
    _score_salary,
    _to_usd,
    score,
)


# ---------------------------------------------------------------------------
# Test scoring config — mirrors the default profile
# ---------------------------------------------------------------------------

TEST_SCORING = ScoringConfig(
    salary_min=80_000,
    salary_max=130_000,
    seniority_high=["senior", "lead", "staff", "principal", "head of", "director"],
    seniority_mid=["mid", "ii", "iii", "2", "3", "specialist", "experienced"],
    stack_keywords={
        "python": 3, "sql": 3, "dbt": 3, "databricks": 3,
        "power bi": 3, "powerbi": 3, "analytics": 2,
        "data modeling": 2, "data model": 2, "snowflake": 2,
        "bigquery": 2, "spark": 2, "airflow": 2, "looker": 2,
        "tableau": 2, "redshift": 1, "metabase": 1,
        "data warehouse": 1, "data platform": 1, "data pipeline": 1,
        "aws": 1, "gcp": 1, "azure": 1, "kafka": 1,
        "pyspark": 2, "mlflow": 1, "streamlit": 2, "fastapi": 2,
    },
    stack_max_score=25,
    location_preferred=[
        "worldwide", "anywhere", "global", "latam", "latin america",
        "brazil", "brasil", " americas",
    ],
    location_neutral_regions=[
        "europe", "emea", "apac", "asia", "africa", "oceania",
        "australia", "india", "uk only", "eu only",
    ],
    location_excluded=["united states", "usa only", "us only", "north america only"],
    company_high=[
        "series b", "series c", "series d", "fintech", "saas", "b2b saas",
        "fully remote", "remote-first", "distributed team",
        "data platform", "data infrastructure", "analytics platform",
    ],
    company_mid=[
        "startup", "scale-up", "scaleup", "growth stage", "series a",
        "financial services", "payments", "e-commerce", "marketplace", "remote",
    ],
)


# ---------------------------------------------------------------------------
# Helper factory
# ---------------------------------------------------------------------------

def make_job(**overrides) -> Job:
    defaults = {
        "url": "https://example.com/job/1",
        "title": "Senior Data Analyst",
        "company": "TestCorp",
        "source": "test",
        "location": "Remote",
        "description": "We need someone skilled in SQL and Python for analytics work.",
        "salary": "",
        "tags": ["python", "sql"],
        "posted_at": None,
    }
    defaults.update(overrides)
    return Job(**defaults)


# ===================================================================
# _score_seniority() tests
# ===================================================================

def test_seniority_senior():
    assert _score_seniority("Senior Data Analyst", TEST_SCORING) == 20


def test_seniority_lead():
    assert _score_seniority("Lead Analytics Engineer", TEST_SCORING) == 20


def test_seniority_specialist():
    assert _score_seniority("Data Specialist", TEST_SCORING) == 10


def test_seniority_no_indicator():
    """Generic title with no seniority keyword scores lowest tier (6)."""
    assert _score_seniority("Data Analyst", TEST_SCORING) == 6


# ===================================================================
# _score_stack() tests
# ===================================================================

def test_stack_all_core_keywords():
    """Description containing python + sql + dbt + databricks should score high."""
    text = "python sql dbt databricks"
    result = _score_stack(text, TEST_SCORING)
    # python(3) + sql(3) + dbt(3) + databricks(3) = 12
    assert result == 12


def test_stack_single_keyword():
    """A single keyword scores proportionally to its weight."""
    assert _score_stack("sql", TEST_SCORING) == 3


def test_stack_no_keywords():
    assert _score_stack("", TEST_SCORING) == 0


def test_stack_tags_counted():
    """Keywords present in the haystack via tags should be counted."""
    job = make_job(
        title="Analyst",
        description="",
        tags=["dbt", "snowflake", "airflow"],
    )
    result = score(job, TEST_SCORING)
    # Tags are joined and lowered into the haystack -> dbt(3) + snowflake(2) + airflow(2) = 7
    assert result.stack >= 7


def test_stack_cap_at_max():
    """Even with every possible keyword, the score must not exceed stack_max_score (25)."""
    text = " ".join(TEST_SCORING.stack_keywords.keys())
    assert _score_stack(text, TEST_SCORING) == TEST_SCORING.stack_max_score


# ===================================================================
# _parse_salary() / _to_usd() tests
# ===================================================================

def test_parse_salary_range():
    lo, hi = _parse_salary("USD 80000-120000")
    assert lo == 80_000
    assert hi == 120_000


def test_parse_salary_single():
    lo, hi = _parse_salary("$100000")
    assert lo == 100_000
    assert hi is None


def test_parse_salary_with_k():
    """'$120k' is expanded to 120000."""
    lo, hi = _parse_salary("$120k")
    assert lo == 120_000
    assert hi is None


def test_parse_salary_range_with_k():
    """'$80K-$130K' is expanded to a proper range."""
    lo, hi = _parse_salary("$80K-$130K")
    assert lo == 80_000
    assert hi == 130_000


def test_parse_salary_none():
    lo, hi = _parse_salary("")
    assert lo is None
    assert hi is None


def test_to_usd_gbp():
    lo, hi = _to_usd(100_000, 120_000, "GBP")
    assert lo == pytest.approx(127_000)
    assert hi == pytest.approx(152_400)


def test_to_usd_eur():
    lo, hi = _to_usd(100_000, None, "EUR")
    assert lo == pytest.approx(109_000)
    assert hi is None


# ===================================================================
# _score_salary() tests
# ===================================================================

def test_salary_in_target_range():
    """$90k-$120k falls perfectly inside $80k-$130k target -> 20."""
    assert _score_salary("USD 90000-120000", TEST_SCORING) == 20


def test_salary_below_minimum():
    """$30k is well below the $80k floor -> low score."""
    result = _score_salary("USD 30000", TEST_SCORING)
    assert result < 8  # worse than unknown


def test_salary_above_target():
    """$200k is above the target range but still worth applying -> 12."""
    assert _score_salary("USD 200000", TEST_SCORING) == 12


def test_salary_empty():
    """No salary info scores the neutral default of 8."""
    assert _score_salary("", TEST_SCORING) == 8
    assert _score_salary(None, TEST_SCORING) == 8


# ===================================================================
# _score_location() tests
# ===================================================================

def test_location_worldwide():
    assert _score_location("Worldwide", "", TEST_SCORING) == 20


def test_location_latam():
    assert _score_location("LATAM", "", TEST_SCORING) == 20
    assert _score_location("Latin America", "", TEST_SCORING) == 20


def test_location_remote_generic():
    """'Remote' with no geo restriction scores 14."""
    assert _score_location("Remote", "", TEST_SCORING) == 14


def test_location_us_only():
    assert _score_location("US only", "", TEST_SCORING) == 0


# ===================================================================
# _score_company() tests
# ===================================================================

def test_company_series_b():
    assert _score_company("we are a series b fintech startup", TEST_SCORING) >= 3


def test_company_fintech():
    assert _score_company("leading fintech company", TEST_SCORING) >= 3


# ===================================================================
# score() integration tests
# ===================================================================

def test_score_returns_total_and_breakdown():
    """score() returns a ScoreBreakdown with total and per-dimension scores."""
    job = make_job()
    result = score(job, TEST_SCORING)
    assert isinstance(result, ScoreBreakdown)
    assert result.total == min(
        result.seniority + result.stack + result.salary + result.location + result.company,
        100,
    )
    assert result.seniority >= 0
    assert result.stack >= 0
    assert result.salary >= 0
    assert result.location >= 0
    assert result.company >= 0


def test_score_total_max_100():
    """Even a perfect job cannot exceed 100."""
    job = make_job(
        title="Senior Lead Staff Data Analyst",
        description=(
            "python sql dbt databricks power bi analytics data modeling "
            "snowflake bigquery spark airflow looker tableau pyspark "
            "streamlit fastapi data warehouse data platform "
            "series b fintech b2b saas fully remote remote-first "
            "data infrastructure analytics platform distributed team "
            "startup scale-up growth stage series a payments "
            "e-commerce marketplace"
        ),
        salary="USD 90000-120000",
        location="Worldwide",
        tags=["python", "sql", "dbt"],
    )
    result = score(job, TEST_SCORING)
    assert result.total <= 100


# ===================================================================
# Custom profile test — proves the system is truly configurable
# ===================================================================

def test_score_with_custom_profile():
    """A different profile changes what scores high."""
    frontend_config = ScoringConfig(
        salary_min=60_000,
        salary_max=100_000,
        seniority_high=["senior", "lead"],
        seniority_mid=["mid"],
        stack_keywords={"react": 3, "typescript": 3, "css": 1},
        stack_max_score=25,
        location_preferred=["europe", "eu", "worldwide"],
        location_neutral_regions=["latam"],
        location_excluded=["us only"],
        company_high=["saas"],
        company_mid=["startup"],
    )
    # A frontend job should score high with the frontend profile
    frontend_job = make_job(
        title="Senior Frontend Engineer",
        description="Build React apps with TypeScript and CSS.",
        salary="USD 80000",
        location="Europe",
    )
    result = score(frontend_job, frontend_config)
    assert result.stack >= 7  # react(3) + typescript(3) + css(1)
    assert result.location == 20  # "europe" is preferred

    # Same job with the data analyst profile should score low on stack
    frontend_job_no_tags = make_job(
        title="Senior Frontend Engineer",
        description="Build React apps with TypeScript and CSS.",
        salary="USD 80000",
        location="Europe",
        tags=[],
    )
    data_result = score(frontend_job_no_tags, TEST_SCORING)
    assert data_result.stack == 0  # no data keywords in description


# ===================================================================
# label() tests
# ===================================================================

def test_label_strong():
    breakdown = ScoreBreakdown(total=85, seniority=20, stack=25, salary=20, location=20, company=0)
    assert breakdown.label() == "Strong match"


def test_label_weak():
    breakdown = ScoreBreakdown(total=30, seniority=6, stack=0, salary=8, location=6, company=10)
    assert breakdown.label() == "Weak"
