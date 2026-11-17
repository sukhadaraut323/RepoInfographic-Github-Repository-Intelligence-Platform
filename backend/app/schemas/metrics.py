"""
Pydantic schemas for Module 5 — Engineering Metrics Engine.

Kept in a dedicated file so Modules 1–4's schema files remain untouched.
`RepositoryMetricsResult` is the sole output contract of this module. It
transforms the structured outputs of Modules 1–4 into explainable,
rule-based scores — every score carries its own numeric value, the
factual evidence it was computed from, and the reasons affecting it.
No AI-generated content and no recommendations are included.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from app.schemas.git_history import GitHistoryResult
from app.schemas.repository import RepositoryMetadata
from app.schemas.static_analysis import StaticAnalysisResult


class RepositoryMetricsRequest(BaseModel):
    """
    Request body for POST /api/v1/repository/metrics.

    Deliberately composed of the exact structured outputs of Modules 1, 3,
    and 4 — Module 5 performs no scanning or GitHub API calls of its own,
    it only transforms what those modules already produced.
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


class SubScore(BaseModel):
    """A single explainable score: a numeric value plus its supporting evidence and reasons."""

    score: float = Field(..., ge=0, le=100, description="Score value, from 0 to 100.")
    evidence: List[str] = Field(
        default_factory=list,
        description="Factual observations the score was computed from (e.g. 'README.md found').",
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Reasons affecting the score, both positive and negative (e.g. 'Missing CONTRIBUTING.md (-15 pts)').",
    )


class RepositoryMetricsResult(BaseModel):
    """
    Structured, explainable engineering metrics and overall health score
    for a repository, derived entirely from Modules 1, 3, and 4's outputs.
    """

    documentation_score: SubScore = Field(
        ..., description="README, LICENSE, CONTRIBUTING, CHANGELOG, docs, API docs."
    )
    codebase_score: SubScore = Field(
        ..., description="Directory organization, project structure, configuration, project detection."
    )
    activity_score: SubScore = Field(
        ..., description="Repository age, commit frequency, contributors, recent activity."
    )
    community_score: SubScore = Field(
        ..., description="Stars, forks, watchers, open issues, contributors."
    )
    maintainability_score: SubScore = Field(
        ..., description="Average file size, directory depth, project organization."
    )
    best_practices_score: SubScore = Field(
        ...,
        description=(
            "CI configuration, Docker, Docker Compose, .gitignore, .editorconfig, "
            ".env.example, pre-commit hooks."
        ),
    )
    overall_health_score: SubScore = Field(
        ..., description="Weighted combination of the six sub-scores above."
    )

    calculated_at: datetime = Field(..., description="Timestamp when these metrics were computed.")
