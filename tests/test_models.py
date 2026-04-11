"""Tests for the Job Pydantic model — field validation, defaults, and coercion."""

from datetime import datetime

import pytest

from job_monitor.core.models import Job


def test_job_creation_with_all_fields():
    """All fields populated — model validates without error."""
    now = datetime(2026, 1, 15, 12, 0, 0)
    job = Job(
        url="https://example.com/job/42",
        title="Senior Data Analyst",
        company="Acme Corp",
        source="remotive",
        location="Remote — Worldwide",
        description="Build dashboards and data pipelines.",
        salary="$100k–$130k",
        tags=["python", "sql", "dbt"],
        posted_at=datetime(2026, 1, 10),
        fetched_at=now,
    )

    assert job.url == "https://example.com/job/42"
    assert job.title == "Senior Data Analyst"
    assert job.company == "Acme Corp"
    assert job.source == "remotive"
    assert job.location == "Remote — Worldwide"
    assert job.salary == "$100k–$130k"
    assert job.tags == ["python", "sql", "dbt"]
    assert job.posted_at == datetime(2026, 1, 10)
    assert job.fetched_at == now


def test_job_defaults():
    """fetched_at defaults to None; validator populates it when explicitly passed a falsy value."""
    # When no value is provided, Pydantic v2 uses the field default without
    # running the validator, so fetched_at stays None.
    job_no_value = Job(
        url="https://example.com/job/1",
        title="Analyst",
        company="TestCo",
        source="himalayas",
    )
    assert job_no_value.fetched_at is None

    # When explicitly passed None (or another falsy value), the validator
    # fires and fills in utcnow.
    before = datetime.utcnow()
    job_explicit = Job(
        url="https://example.com/job/1",
        title="Analyst",
        company="TestCo",
        source="himalayas",
        fetched_at=None,
    )
    after = datetime.utcnow()
    assert job_explicit.fetched_at is not None
    assert before <= job_explicit.fetched_at <= after


def test_job_tags_from_string():
    """Comma-separated string gets coerced to a list of stripped tags."""
    job = Job(
        url="https://example.com/job/2",
        title="Analyst",
        company="TestCo",
        source="himalayas",
        tags="python, sql, dbt",
    )
    assert job.tags == ["python", "sql", "dbt"]


def test_job_tags_from_list():
    """Tags passed as a list go through unchanged."""
    tags_in = ["python", "sql"]
    job = Job(
        url="https://example.com/job/3",
        title="Analyst",
        company="TestCo",
        source="himalayas",
        tags=tags_in,
    )
    assert job.tags == ["python", "sql"]


@pytest.mark.parametrize("tags_input", [None, "", "  ,  , "])
def test_job_tags_none_or_empty(tags_input):
    """None, empty string, or whitespace-only commas all become an empty list."""
    job = Job(
        url="https://example.com/job/4",
        title="Analyst",
        company="TestCo",
        source="himalayas",
        tags=tags_input,
    )
    assert job.tags == []


def test_job_optional_fields():
    """salary, posted_at, location, description can be None."""
    job = Job(
        url="https://example.com/job/5",
        title="Analyst",
        company="TestCo",
        source="himalayas",
    )
    assert job.salary is None
    assert job.posted_at is None
    assert job.location is None
    assert job.description is None
