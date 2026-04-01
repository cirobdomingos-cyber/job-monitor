from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class Job(BaseModel):
    url: str
    title: str
    company: str
    source: str  # "himalayas" | "remotive" | "weworkremotely" | "remoteco"
    location: Optional[str] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    tags: list[str] = []
    posted_at: Optional[datetime] = None
    fetched_at: datetime = None  # set by runner

    @field_validator("fetched_at", mode="before")
    @classmethod
    def default_fetched_at(cls, v):
        return v or datetime.utcnow()

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v or []
