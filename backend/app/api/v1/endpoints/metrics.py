"""
API endpoint for Module 5 — Engineering Metrics Engine.

Exposes a single route:
    POST /api/v1/repository/metrics

This endpoint performs pure computation over the request body (the
structured outputs of Modules 1, 3, and 4) — no filesystem access, no
git operations, and no GitHub API calls happen here, so it is a regular
`async def` path operation.
"""

import logging

from fastapi import APIRouter, Depends, status

from app.core.config import get_settings
from app.schemas.metrics import RepositoryMetricsRequest, RepositoryMetricsResult
from app.services.activity_analyzer import ActivityAnalyzer
from app.services.best_practices_analyzer import BestPracticesAnalyzer
from app.services.codebase_analyzer import CodebaseAnalyzer
from app.services.community_analyzer import CommunityAnalyzer
from app.services.documentation_analyzer import DocumentationAnalyzer
from app.services.health_score_calculator import HealthScoreCalculator
from app.services.repository_metrics_service import RepositoryMetricsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repository", tags=["Engineering Metrics"])


def get_repository_metrics_service() -> RepositoryMetricsService:
    """
    Dependency provider for RepositoryMetricsService.

    Kept as a function (rather than a module-level singleton) so tests can
    override it via FastAPI's `app.dependency_overrides`.
    """
    settings = get_settings()
    health_score_calculator = HealthScoreCalculator(
        weight_documentation=settings.metrics_weight_documentation,
        weight_codebase=settings.metrics_weight_codebase,
        weight_activity=settings.metrics_weight_activity,
        weight_community=settings.metrics_weight_community,
        weight_maintainability=settings.metrics_weight_maintainability,
        weight_best_practices=settings.metrics_weight_best_practices,
    )
    return RepositoryMetricsService(
        documentation_analyzer=DocumentationAnalyzer(),
        codebase_analyzer=CodebaseAnalyzer(),
        activity_analyzer=ActivityAnalyzer(),
        community_analyzer=CommunityAnalyzer(),
        best_practices_analyzer=BestPracticesAnalyzer(),
        health_score_calculator=health_score_calculator,
    )


@router.post(
    "/metrics",
    response_model=RepositoryMetricsResult,
    status_code=status.HTTP_200_OK,
    summary="Compute explainable engineering metrics and the overall health score",
    description=(
        "Transforms the structured outputs of Modules 1 (metadata), 3 "
        "(static analysis), and 4 (git history) into six explainable, "
        "rule-based scores plus an overall Repository Health Score. "
        "Every score includes its numeric value, the evidence it was "
        "computed from, and the reasons affecting it. No AI is used and "
        "no recommendations are generated."
    ),
)
async def get_repository_metrics(
    request: RepositoryMetricsRequest,
    service: RepositoryMetricsService = Depends(get_repository_metrics_service),
) -> RepositoryMetricsResult:
    """Compute and return engineering metrics for the given module outputs."""
    return service.compute_metrics(
        repository_metadata=request.repository_metadata,
        static_analysis_result=request.static_analysis_result,
        git_history_result=request.git_history_result,
    )
