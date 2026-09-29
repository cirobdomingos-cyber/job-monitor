"""
profile.py — User-configurable search profile loaded from YAML.

A profile defines what jobs to look for (filters), how to rank them (scoring),
and which scrapers to use. This replaces hardcoded values in config.py and
scorer.py, letting any user define their own search criteria.

Usage:
    profile = load_profile("profiles/default.yaml")
    profile = load_profile()  # loads default.yaml from profiles/ directory
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

PROFILES_DIR = Path(__file__).resolve().parent.parent.parent / "profiles"


@dataclass
class FilterConfig:
    title_keywords: list[str] = field(default_factory=list)
    title_exclusions: list[str] = field(default_factory=list)
    body_keywords: list[str] = field(default_factory=list)
    geo_exclusions: list[str] = field(default_factory=list)


@dataclass
class ScoringConfig:
    salary_min: int = 80_000
    salary_max: int = 130_000
    seniority_high: list[str] = field(default_factory=lambda: [
        "senior", "lead", "staff", "principal", "head of", "director",
    ])
    seniority_mid: list[str] = field(default_factory=lambda: [
        "mid", "ii", "iii", "2", "3", "specialist", "experienced",
    ])
    stack_keywords: dict[str, int] = field(default_factory=dict)
    stack_max_score: int = 25
    location_preferred: list[str] = field(default_factory=lambda: [
        "worldwide", "anywhere", "global",
    ])
    location_neutral_regions: list[str] = field(default_factory=lambda: [
        "europe", "emea", "apac", "asia", "africa", "oceania",
        "australia", "india", "uk only", "eu only",
    ])
    location_excluded: list[str] = field(default_factory=lambda: [
        "united states", "usa only", "us only", "north america only",
    ])
    company_high: list[str] = field(default_factory=list)
    company_mid: list[str] = field(default_factory=list)


@dataclass
class Profile:
    name: str = "default"
    filters: FilterConfig = field(default_factory=FilterConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    enabled_scrapers: dict[str, bool] = field(default_factory=dict)


def load_profile(path: Optional[str] = None) -> Profile:
    """Load a profile from a YAML file.

    Args:
        path: Path to YAML file. If None, loads profiles/default.yaml.
              If just a name (no slashes), looks in profiles/ directory.
    """
    if path is None:
        filepath = PROFILES_DIR / "default.yaml"
    elif "/" not in path and "\\" not in path and not Path(path).exists():
        filepath = PROFILES_DIR / path
        if not filepath.suffix:
            filepath = filepath.with_suffix(".yaml")
    else:
        filepath = Path(path)

    if not filepath.exists():
        raise FileNotFoundError(f"Profile not found: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return _parse_profile(raw)


def list_profiles() -> list[str]:
    """Return names of available profiles in the profiles/ directory."""
    if not PROFILES_DIR.exists():
        return []
    return sorted(
        p.stem for p in PROFILES_DIR.glob("*.yaml")
    )


def save_profile(profile: Profile, name: str) -> Path:
    """Save a Profile to a YAML file in the profiles/ directory.

    Args:
        profile: The Profile object to save.
        name: Filename stem (without .yaml extension).

    Returns:
        Path to the saved file.
    """
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = PROFILES_DIR / f"{name}.yaml"

    data = {
        "name": profile.name,
        "filters": {
            "title_keywords": profile.filters.title_keywords,
            "title_exclusions": profile.filters.title_exclusions,
            "body_keywords": profile.filters.body_keywords,
            "geo_exclusions": profile.filters.geo_exclusions,
        },
        "scoring": {
            "salary_min": profile.scoring.salary_min,
            "salary_max": profile.scoring.salary_max,
            "seniority_high": profile.scoring.seniority_high,
            "seniority_mid": profile.scoring.seniority_mid,
            "stack_keywords": profile.scoring.stack_keywords,
            "stack_max_score": profile.scoring.stack_max_score,
            "location_preferred": profile.scoring.location_preferred,
            "location_neutral_regions": profile.scoring.location_neutral_regions,
            "location_excluded": profile.scoring.location_excluded,
            "company_high": profile.scoring.company_high,
            "company_mid": profile.scoring.company_mid,
        },
        "scrapers": {
            "enabled": profile.enabled_scrapers,
        },
    }

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return filepath


def delete_profile(name: str) -> bool:
    """Delete a profile YAML file. Returns True if deleted, False if not found."""
    filepath = PROFILES_DIR / f"{name}.yaml"
    if filepath.exists():
        filepath.unlink()
        return True
    return False


def _parse_profile(raw: dict) -> Profile:
    """Convert raw YAML dict into a Profile object."""
    # Build a defaults instance to fall back on for missing YAML keys
    _defaults = ScoringConfig()

    filt_raw = raw.get("filters", {})
    filters = FilterConfig(
        title_keywords=filt_raw.get("title_keywords", []),
        title_exclusions=filt_raw.get("title_exclusions", []),
        body_keywords=filt_raw.get("body_keywords", []),
        geo_exclusions=filt_raw.get("geo_exclusions", []),
    )

    score_raw = raw.get("scoring", {})
    scoring = ScoringConfig(
        salary_min=score_raw.get("salary_min", _defaults.salary_min),
        salary_max=score_raw.get("salary_max", _defaults.salary_max),
        seniority_high=score_raw.get("seniority_high", _defaults.seniority_high),
        seniority_mid=score_raw.get("seniority_mid", _defaults.seniority_mid),
        stack_keywords=score_raw.get("stack_keywords", _defaults.stack_keywords),
        stack_max_score=score_raw.get("stack_max_score", _defaults.stack_max_score),
        location_preferred=score_raw.get("location_preferred", _defaults.location_preferred),
        location_neutral_regions=score_raw.get("location_neutral_regions", _defaults.location_neutral_regions),
        location_excluded=score_raw.get("location_excluded", _defaults.location_excluded),
        company_high=score_raw.get("company_high", _defaults.company_high),
        company_mid=score_raw.get("company_mid", _defaults.company_mid),
    )

    scrapers_raw = raw.get("scrapers", {}).get("enabled", {})

    return Profile(
        name=raw.get("name", "default"),
        filters=filters,
        scoring=scoring,
        enabled_scrapers=scrapers_raw,
    )
