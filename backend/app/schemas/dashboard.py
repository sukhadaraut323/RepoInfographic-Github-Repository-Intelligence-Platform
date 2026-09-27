"""
Pydantic schemas for the Repository Orchestrator.

Exposes the request/response contract for:
    POST /api/v1/dashboard/analyze

Kept in a dedicated file (separate from Modules 1-6's schema files) so
none of their stable request/response contracts are touched. Every field
here is either the single orchestrator input (`repository_url`) or a
direct composition of Modules 1-6's own already-defined output schemas —
the orchestrator introduces no new engineering data of its own.
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.analytics import AnalyticsDashboardResult
from app.schemas.clone_result import RepositoryCloneResult
from app.schemas.git_history import GitHistoryResult
from app.schemas.metrics import RepositoryMetricsResult
from app.schemas.repository import RepositoryMetadata
from app.schemas.static_analysis import StaticAnalysisResult


class DashboardAnalyzeRequest(BaseModel):
    """Request body for POST /api/v1/dashboard/analyze."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository URL.",
        examples=["https://github.com/fastapi/fastapi"],
        min_length=1,
    )


class DashboardData(BaseModel):
    """
    Unified result of running the complete Modules 1-6 analysis pipeline
    for a single repository.

    Every field is the exact, unmodified output schema already produced
    by its corresponding module - the orchestrator only sequences the
    calls and assembles the results, it computes nothing new itself.
    """

    repository_metadata: RepositoryMetadata = Field(..., description="Output of Module 1.")
    clone_result: RepositoryCloneResult = Field(..., description="Output of Module 2.")
    static_analysis_result: StaticAnalysisResult = Field(..., description="Output of Module 3.")
    git_history_result: GitHistoryResult = Field(..., description="Output of Module 4.")
    repository_metrics_result: RepositoryMetricsResult = Field(..., description="Output of Module 5.")
    analytics: AnalyticsDashboardResult = Field(..., description="Output of Module 6.")
    generated_at: datetime = Field(..., description="Timestamp when this dashboard payload was assembled.")


class DashboardAnalyzeSuccessResponse(BaseModel):
    """Standard success envelope for POST /api/v1/dashboard/analyze."""

    success: Literal[True] = True
    message: str = Field(..., description="Human-readable summary of the outcome.")
    data: DashboardData


class DashboardErrorDetail(BaseModel):
    """Structured, non-sensitive detail about a failed pipeline stage."""

    code: str = Field(..., description="Stable machine-readable error code.")
    detail: str = Field(..., description="Human-readable explanation, safe to display to a client.")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional additional non-sensitive context."
    )


class DashboardAnalyzeErrorResponse(BaseModel):
    """Standard error envelope for POST /api/v1/dashboard/analyze."""

    success: Literal[False] = False
    message: str = Field(..., description="Human-readable summary of the failure.")
    error: DashboardErrorDetail
