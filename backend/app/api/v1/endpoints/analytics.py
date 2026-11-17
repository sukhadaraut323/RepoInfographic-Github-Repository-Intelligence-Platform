"""
API endpoint for Module 6 — Analytics Engine.

Exposes a single route:
    POST /api/v1/repository/analytics

This endpoint performs pure computation over the request body (the
structured outputs of Modules 1, 3, 4, and 5) — no filesystem access, no
git operations, and no GitHub API calls happen here, so it is a regular
`async def` path operation.
"""

import logging

from fastapi import APIRouter, Depends, status

from app.core.config import get_settings
from app.schemas.analytics import AnalyticsDashboardResult, AnalyticsRequest
from app.services.analytics_service import AnalyticsService
from app.services.commit_timeline_formatter import CommitTimelineFormatter
from app.services.file_type_distribution_formatter import FileTypeDistributionFormatter
from app.services.health_gauge_formatter import HealthGaugeFormatter
from app.services.language_distribution_formatter import LanguageDistributionFormatter
from app.services.largest_directories_formatter import LargestDirectoriesFormatter
from app.services.overview_cards_formatter import OverviewCardsFormatter
from app.services.repository_timeline_formatter import RepositoryTimelineFormatter
from app.services.score_breakdown_formatter import ScoreBreakdownFormatter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repository", tags=["Analytics Engine"])


def get_analytics_service() -> AnalyticsService:
    """
    Dependency provider for AnalyticsService.

    Kept as a function (rather than a module-level singleton) so tests can
    override it via FastAPI's `app.dependency_overrides`.
    """
    settings = get_settings()
    return AnalyticsService(
        language_distribution_formatter=LanguageDistributionFormatter(),
        commit_timeline_formatter=CommitTimelineFormatter(
            monthly_point_limit=settings.analytics_commit_timeline_monthly_point_limit
        ),
        overview_cards_formatter=OverviewCardsFormatter(),
        health_gauge_formatter=HealthGaugeFormatter(
            excellent_threshold=settings.analytics_health_status_excellent_threshold,
            good_threshold=settings.analytics_health_status_good_threshold,
            fair_threshold=settings.analytics_health_status_fair_threshold,
        ),
        score_breakdown_formatter=ScoreBreakdownFormatter(),
        repository_timeline_formatter=RepositoryTimelineFormatter(),
        file_type_distribution_formatter=FileTypeDistributionFormatter(),
        largest_directories_formatter=LargestDirectoriesFormatter(
            limit=settings.analytics_largest_directories_limit
        ),
    )


@router.post(
    "/analytics",
    response_model=AnalyticsDashboardResult,
    status_code=status.HTTP_200_OK,
    summary="Produce chart-ready dashboard analytics from Modules 1, 3, 4, and 5's outputs",
    description=(
        "Transforms the structured outputs of Modules 1 (metadata), 3 "
        "(static analysis), 4 (git history), and 5 (engineering metrics) "
        "into eight chart-ready analytics payloads (language distribution, "
        "commit timeline, overview cards, health gauge, score breakdown, "
        "repository timeline, file type distribution, and largest "
        "directories) suitable for direct use with React/Recharts. No "
        "GitHub API calls, filesystem access, or new metric computation "
        "happen here — only formatting and aggregation of existing outputs."
    ),
)
async def get_repository_analytics(
    request: AnalyticsRequest,
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsDashboardResult:
    """Build and return the chart-ready analytics dashboard payload."""
    return service.build_dashboard(
        repository_metadata=request.repository_metadata,
        static_analysis_result=request.static_analysis_result,
        git_history_result=request.git_history_result,
        repository_metrics_result=request.repository_metrics_result,
    )
