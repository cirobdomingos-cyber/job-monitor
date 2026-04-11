"""Tests for deduplication logic — URL hashing and filter_new."""

from unittest.mock import patch

import pytest

from job_monitor.core.dedup import _url_hash, filter_new
from job_monitor.core.models import Job


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_job(**overrides) -> Job:
    defaults = {
        "url": "https://example.com/job/1",
        "title": "Senior Data Analyst",
        "company": "TestCorp",
        "source": "test",
        "location": "Remote",
        "description": "SQL and Python analytics role.",
        "salary": "",
        "tags": ["python", "sql"],
        "posted_at": None,
    }
    defaults.update(overrides)
    return Job(**defaults)


# ---------------------------------------------------------------------------
# URL hashing
# ---------------------------------------------------------------------------

def test_url_hash_deterministic():
    """Same URL always produces the same hash."""
    url = "https://example.com/job/42"
    assert _url_hash(url) == _url_hash(url)


def test_url_hash_different_urls():
    """Different URLs produce different hashes."""
    h1 = _url_hash("https://example.com/job/1")
    h2 = _url_hash("https://example.com/job/2")
    assert h1 != h2


def test_url_hash_type():
    """Hash is a hex-digest string."""
    h = _url_hash("https://example.com")
    assert isinstance(h, str)
    # SHA-256 hex digest is 64 chars
    assert len(h) == 64
    # All chars are valid hex
    assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# filter_new  (DB interactions mocked)
# ---------------------------------------------------------------------------

@patch("job_monitor.core.dedup.mark_seen")
@patch("job_monitor.core.dedup.get_seen_urls")
def test_filter_new_all_new(mock_get_seen, mock_mark):
    """When seen_urls is empty, every job passes through."""
    mock_get_seen.return_value = set()

    jobs = [
        make_job(url="https://example.com/job/1"),
        make_job(url="https://example.com/job/2"),
    ]
    result = filter_new(jobs)

    assert len(result) == 2
    assert mock_mark.call_count == 2


@patch("job_monitor.core.dedup.mark_seen")
@patch("job_monitor.core.dedup.get_seen_urls")
def test_filter_new_removes_seen(mock_get_seen, mock_mark):
    """Jobs whose URL hash is already in seen_urls are filtered out."""
    url = "https://example.com/job/1"
    mock_get_seen.return_value = {_url_hash(url)}

    jobs = [make_job(url=url)]
    result = filter_new(jobs)

    assert result == []
    mock_mark.assert_not_called()


@patch("job_monitor.core.dedup.mark_seen")
@patch("job_monitor.core.dedup.get_seen_urls")
def test_filter_new_mixed(mock_get_seen, mock_mark):
    """Mix of new and previously-seen jobs — only new ones returned."""
    seen_url = "https://example.com/job/old"
    new_url = "https://example.com/job/new"
    mock_get_seen.return_value = {_url_hash(seen_url)}

    jobs = [
        make_job(url=seen_url),
        make_job(url=new_url),
    ]
    result = filter_new(jobs)

    assert len(result) == 1
    assert result[0].url == new_url
    assert mock_mark.call_count == 1
