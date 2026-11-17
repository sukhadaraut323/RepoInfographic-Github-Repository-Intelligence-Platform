"""
Pydantic schemas for Module 4 — Git History Analysis.

Kept in a dedicated file so Modules 1–3's schema files remain untouched.
`GitHistoryResult` is the sole output contract of this module. It reports
only directly observable facts and simple arithmetic derived from local
git commit metadata (dates, authors, branches, counts) — no blame,
release, merge, code-ownership, or AI-derived analysis belongs here.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ActivityLevel(str, Enum):
    """Coarse classification of how recently/frequently the repository has been committed to."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    DORMANT = "Dormant"


class GitHistoryRequest(BaseModel):
    """Request body for POST /api/v1/repository/history."""

    local_path: str = Field(
        ...,
        description=(
            "Local filesystem path to a previously cloned repository, "
            "as produced by Module 2 (RepositoryCloneResult.local_path)."
        ),
        examples=["workspace/fastapi_fastapi"],
        min_length=1,
    )


class MonthlyCommitCount(BaseModel):
    """Commit count for a single calendar month."""

    month: str = Field(..., description='Calendar month in "YYYY-MM" format.', examples=["2024-03"])
    commit_count: int = Field(..., ge=0, description="Number of commits made during this month.")


class GitHistoryResult(BaseModel):
    """Structured engineering history derived from local git commit metadata."""

    local_path: str = Field(..., description="Path to the repository that was analyzed.")

    repository_age_days: int = Field(
        ..., ge=0, description="Days elapsed since the first commit, up to now."
    )
    first_commit_date: Optional[datetime] = Field(
        default=None, description="Timestamp of the earliest commit, if any."
    )
    latest_commit_date: Optional[datetime] = Field(
        default=None, description="Timestamp of the most recent commit, if any."
    )

    total_commits: int = Field(..., ge=0, description="Total number of commits across all branches.")
    unique_contributors: int = Field(
        ..., ge=0, description="Number of distinct commit authors (by email)."
    )
    total_branches: int = Field(..., ge=0, description="Total number of branches in the repository.")
    default_branch: Optional[str] = Field(
        default=None, description="The repository's default/primary branch, if determinable."
    )

    average_commits_per_day: float = Field(..., ge=0, description="Total commits divided by repository age in days.")
    average_commits_per_week: float = Field(..., ge=0, description="Average commits per 7-day period.")
    average_commits_per_month: float = Field(..., ge=0, description="Average commits per ~30-day period.")

    monthly_commit_timeline: List[MonthlyCommitCount] = Field(
        default_factory=list,
        description="Commit counts per calendar month, spanning from the first to the latest commit.",
    )

    recent_activity_level: ActivityLevel = Field(
        ..., description="Coarse recent-activity classification based on commit frequency."
    )

    analyzed_at: datetime = Field(..., description="Timestamp when this analysis was performed.")
