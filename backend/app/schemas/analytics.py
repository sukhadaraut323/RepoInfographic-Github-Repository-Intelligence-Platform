"""
Pydantic schemas for Module 6 — Analytics Engine.

Kept in a dedicated file so Modules 1–5's schema files remain untouched.
Every model here is a plain, chart-ready shape intended to be handed
directly to a React/Recharts component with no further transformation —
field names are chosen to match common Recharts conventions (e.g. `name`
and `value` for pie/bar charts).

Module 6 computes nothing new: every value here is either copied directly
from, or is simple formatting/aggregation of, the structured outputs of
Modules 1, 3, 4, and 5. No new engineering metrics are introduced.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.git_history import GitHistoryResult
from app.schemas.metrics import RepositoryMetricsResult
from app.schemas.repository import RepositoryMetadata
from app.schemas.static_analysis import StaticAnalysisResult


class AnalyticsRequest(BaseModel):
    """
    Request body for POST /api/v1/repository/analytics.

    Composed of the exact structured outputs of Modules 1, 3, 4, and 5 —
    Module 6 performs no GitHub API calls, no filesystem reads, and no
    repository analysis of its own.
    """

    repository_metadata: RepositoryMetadata = Field(
        ..., description="Output of Module 1 (GitHub Repository Metadata Collector)."
    )
    static_analysis_result: StaticAnalysisResult = Field(
        ..., description="Output of Module 3 (Static Code Analysis)."
    )
    git_history_result: GitHistoryResult = Field(
        ..., description="Output of Module 4 (Git History Analysis)."
    )
    repository_metrics_result: RepositoryMetricsResult = Field(
        ..., description="Output of Module 5 (Engineering Metrics Engine)."
    )


# --- 1. Language Distribution ------------------------------------------------


class LanguageDistributionSlice(BaseModel):
    """One slice of a language-distribution pie/bar chart."""

    name: str = Field(..., description="Language name.")
    value: int = Field(..., ge=0, description="Number of files detected for this language.")
    percentage: float = Field(..., ge=0, le=100, description="Share of supported source files.")


# --- 2. Commit Timeline ------------------------------------------------------


class CommitTimelinePoint(BaseModel):
    """One point on the monthly commit-count timeline chart."""

    month: str = Field(..., description='Calendar month in "YYYY-MM" format.')
    commits: int = Field(..., ge=0, description="Number of commits made during this month.")


# --- 3. Repository Overview Cards --------------------------------------------


class OverviewCard(BaseModel):
    """A single KPI card for a dashboard overview strip."""

    label: str = Field(..., description="Human-readable card label.")
    value: float = Field(..., description="Numeric value to display.")
    unit: Optional[str] = Field(default=None, description="Optional unit/suffix (e.g. 'files', '%').")


# --- 4. Health Gauge ----------------------------------------------------------


class HealthGauge(BaseModel):
    """Gauge-chart-ready representation of the overall health score."""

    value: float = Field(..., ge=0, le=100, description="Overall health score (0-100).")
    min: float = Field(default=0, description="Gauge minimum.")
    max: float = Field(default=100, description="Gauge maximum.")
    label: str = Field(default="Repository Health Score", description="Gauge label.")
    status: str = Field(
        ..., description="Presentational status band for gauge coloring (Excellent/Good/Fair/Poor)."
    )


# --- 5. Score Breakdown -------------------------------------------------------


class ScoreBreakdownEntry(BaseModel):
    """One bar/axis of a score-breakdown bar or radar chart."""

    category: str = Field(..., description="Score category name (e.g. 'Documentation').")
    score: float = Field(..., ge=0, le=100, description="Score value, from 0 to 100.")


# --- 6. Repository Timeline ----------------------------------------------------


class RepositoryTimelineEvent(BaseModel):
    """A single dated milestone event for a repository timeline chart."""

    date: datetime = Field(..., description="Timestamp of the event.")
    label: str = Field(..., description="Human-readable event label (e.g. 'First Commit').")


# --- 7. File Type Distribution -------------------------------------------------


class FileTypeDistributionSlice(BaseModel):
    """One slice of a broad file-type-distribution pie chart (source vs. other)."""

    name: str = Field(..., description="File category name.")
    value: int = Field(..., ge=0, description="Number of files in this category.")
    percentage: float = Field(..., ge=0, le=100, description="Share of total files.")


# --- 8. Largest Directories ----------------------------------------------------


class LargestDirectoryEntry(BaseModel):
    """One bar of a largest-directories bar chart."""

    name: str = Field(..., description="Directory name.")
    path: str = Field(..., description="Path of the directory relative to the repository root.")
    file_count: int = Field(..., ge=0, description="Number of files contained within this directory (recursively).")


# --- Aggregate result ----------------------------------------------------------


class AnalyticsDashboardResult(BaseModel):
    """The complete set of chart-ready analytics for a repository dashboard."""

    language_distribution: List[LanguageDistributionSlice] = Field(default_factory=list)
    commit_timeline: List[CommitTimelinePoint] = Field(default_factory=list)
    overview_cards: List[OverviewCard] = Field(default_factory=list)
    health_gauge: HealthGauge
    score_breakdown: List[ScoreBreakdownEntry] = Field(default_factory=list)
    repository_timeline: List[RepositoryTimelineEvent] = Field(default_factory=list)
    file_type_distribution: List[FileTypeDistributionSlice] = Field(default_factory=list)
    largest_directories: List[LargestDirectoryEntry] = Field(default_factory=list)

    generated_at: datetime = Field(..., description="Timestamp when this analytics payload was generated.")
