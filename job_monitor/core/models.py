from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    # Scoring (populated by runner after filtering)
    score: Optional[int] = None                   # 0–100
    score_breakdown: Optional[str] = None         # JSON string of dimension scores

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v or []
