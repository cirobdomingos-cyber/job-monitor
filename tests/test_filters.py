"""Tests for job_monitor.core.filters — title, body, geo, and pipeline filters."""

from __future__ import annotations

import pytest

from job_monitor.core.filters import (
    apply,
    is_geo_excluded,
    matches_keywords,
    matches_title,
    title_not_excluded,
)
from job_monitor.core.models import Job
from job_monitor.core.profile import FilterConfig


# ---------------------------------------------------------------------------
# Test config — minimal keyword sets for isolated testing
# ---------------------------------------------------------------------------

TEST_TITLE_KEYWORDS = ["data analyst", "analytics engineer", "senior analyst"]
TEST_TITLE_EXCLUSIONS = ["intern", "junior", "entry level", "entry-level", "trainee"]
TEST_BODY_KEYWORDS = ["sql", "python", "dbt", "analytics", "spark"]
TEST_GEO_EXCLUSIONS = [
    "must be located in the us", "us only", "uk only",
    "united states only", "north america only",
]

TEST_FILTER_CONFIG = FilterConfig(
    title_keywords=TEST_TITLE_KEYWORDS,
    title_exclusions=TEST_TITLE_EXCLUSIONS,
    body_keywords=TEST_BODY_KEYWORDS,
    geo_exclusions=TEST_GEO_EXCLUSIONS,
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
        "description": "We need someone skilled in SQL and Python for analytics.",
        "salary": "",
        "tags": ["python", "sql"],
        "posted_at": None,
    }
    defaults.update(overrides)
    return Job(**defaults)


# ---------------------------------------------------------------------------
# matches_title() tests
# ---------------------------------------------------------------------------

def test_matches_title_exact_keyword():
    """Title containing a keyword verbatim should match."""
    job = make_job(title="Senior Data Analyst at Acme")
    assert matches_title(job, TEST_TITLE_KEYWORDS) is True


def test_matches_title_case_insensitive():
    """Matching is case-insensitive — uppercase titles still match."""
    job = make_job(title="ANALYTICS ENGINEER")
    assert matches_title(job, TEST_TITLE_KEYWORDS) is True


def test_matches_title_no_match():
    """Title without any target keyword should not match."""
    job = make_job(title="Software Engineer")
    assert matches_title(job, TEST_TITLE_KEYWORDS) is False


def test_matches_title_partial_keyword():
    """'Data Analyst' is a substring of a configured keyword and should match."""
    job = make_job(title="Data Analyst")
    assert matches_title(job, TEST_TITLE_KEYWORDS) is True


# ---------------------------------------------------------------------------
# title_not_excluded() tests
# ---------------------------------------------------------------------------

def test_title_excluded_junior():
    """Titles containing 'junior' should be excluded."""
    job = make_job(title="Junior Data Analyst")
    assert title_not_excluded(job, TEST_TITLE_EXCLUSIONS) is False


def test_title_excluded_intern():
    """Titles containing 'intern' should be excluded."""
    job = make_job(title="Data Analyst Intern")
    assert title_not_excluded(job, TEST_TITLE_EXCLUSIONS) is False


def test_title_not_excluded_senior():
    """Senior roles should pass the exclusion filter."""
    job = make_job(title="Senior Data Analyst")
    assert title_not_excluded(job, TEST_TITLE_EXCLUSIONS) is True


def test_title_excluded_entry_level():
    """Titles containing 'entry level' should be excluded."""
    job = make_job(title="Entry Level Analyst")
    assert title_not_excluded(job, TEST_TITLE_EXCLUSIONS) is False


# ---------------------------------------------------------------------------
# matches_keywords() tests (body/description matching)
# ---------------------------------------------------------------------------

def test_body_matches_sql():
    """Description mentioning SQL should match body keywords."""
    job = make_job(description="Experience with SQL required.", tags=[])
    assert matches_keywords(job, TEST_BODY_KEYWORDS) is True


def test_body_matches_python_in_tags():
    """'python' present in tags should match even with empty description."""
    job = make_job(description="", tags=["python"])
    assert matches_keywords(job, TEST_BODY_KEYWORDS) is True


def test_body_no_match():
    """Description and tags with no relevant keywords should not match."""
    job = make_job(
        description="Looking for a great communicator.",
        tags=["leadership", "management"],
    )
    assert matches_keywords(job, TEST_BODY_KEYWORDS) is False


def test_body_matches_html_stripped():
    """HTML tags are stripped — 'python' inside <b> still matches."""
    job = make_job(description="We use <b>Python</b> and Spark.", tags=[])
    assert matches_keywords(job, TEST_BODY_KEYWORDS) is True


# ---------------------------------------------------------------------------
# is_geo_excluded() tests
# ---------------------------------------------------------------------------

def test_geo_excluded_us_only():
    """Description with US-only residency requirement should be excluded."""
    job = make_job(
        description="Candidate must be located in the US.",
        location="Remote",
    )
    assert is_geo_excluded(job, TEST_GEO_EXCLUSIONS) is True


def test_geo_excluded_uk_only():
    """'uk only' in location IS geo-excluded."""
    job = make_job(description="", location="UK Only")
    assert is_geo_excluded(job, TEST_GEO_EXCLUSIONS) is True


def test_geo_not_excluded_worldwide():
    """A job open worldwide should not be geo-excluded."""
    job = make_job(description="Open to candidates worldwide.", location="Worldwide")
    assert is_geo_excluded(job, TEST_GEO_EXCLUSIONS) is False


def test_geo_not_excluded_remote():
    """A plain 'Remote' job with no restrictions should not be geo-excluded."""
    job = make_job(description="Fully remote position.", location="Remote")
    assert is_geo_excluded(job, TEST_GEO_EXCLUSIONS) is False


# ---------------------------------------------------------------------------
# apply() pipeline test
# ---------------------------------------------------------------------------

def test_apply_full_pipeline():
    """Batch of 5 jobs — only the valid ones survive all filter stages."""
    jobs = [
        # PASS: good title + body keywords + no geo restriction
        make_job(
            title="Senior Data Analyst",
            description="Must know SQL and Python.",
            location="Remote",
        ),
        # FAIL: title does not match any keyword
        make_job(
            title="Software Engineer",
            description="Must know SQL and Python.",
            location="Remote",
        ),
        # FAIL: title matches but body has no relevant keyword
        make_job(
            title="Analytics Engineer",
            description="Great communicator needed.",
            tags=[],
            location="Remote",
        ),
        # FAIL: title + body match but geo-excluded (US only)
        make_job(
            title="Data Analyst",
            description="Experience with SQL. Must be located in the US.",
            location="Remote, US",
        ),
        # FAIL: junior title is excluded
        make_job(
            title="Junior Data Analyst",
            description="SQL and Python required.",
            location="Remote",
        ),
    ]
    filtered = apply(jobs, TEST_FILTER_CONFIG)
    assert len(filtered) == 1
    assert filtered[0].title == "Senior Data Analyst"
