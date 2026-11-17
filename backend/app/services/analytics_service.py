"""
Service layer for Module 6 — Analytics Engine.

Orchestrates all eight formatters to transform Modules 1, 3, 4, and 5's
structured outputs into a single chart-ready `AnalyticsDashboardResult`.
Performs no GitHub API calls, no filesystem access, and no repository
analysis of its own — every value is either copied directly from, or is
simple formatting/aggregation of, an upstream module's already-computed
output.
"""

import logging
from datetime import datetime, timezone

from app.schemas.analytics import AnalyticsDashboardResult
from app.schemas.git_history import GitHistoryResult
from app.schemas.metrics import RepositoryMetricsResult
from app.schemas.repository import RepositoryMetadata
from app.schemas.static_analysis import StaticAnalysisResult
from app.services.commit_timeline_formatter import CommitTimelineFormatter
from app.services.file_type_distribution_formatter import FileTypeDistributionFormatter
from app.services.health_gauge_formatter import HealthGaugeFormatter
from app.services.language_distribution_formatter import LanguageDistributionFormatter
from app.services.largest_directories_formatter import LargestDirectoriesFormatter
from app.services.overview_cards_formatter import OverviewCardsFormatter
from app.services.repository_timeline_formatter import RepositoryTimelineFormatter
from app.services.score_breakdown_formatter import ScoreBreakdownFormatter

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Produces the full chart-ready analytics dashboard payload."""

    def __init__(
        self,
        language_distribution_formatter: LanguageDistributionFormatter,
        commit_timeline_formatter: CommitTimelineFormatter,
        overview_cards_formatter: OverviewCardsFormatter,
        health_gauge_formatter: HealthGaugeFormatter,
        score_breakdown_formatter: ScoreBreakdownFormatter,
        repository_timeline_formatter: RepositoryTimelineFormatter,
        file_type_distribution_formatter: FileTypeDistributionFormatter,
        largest_directories_formatter: LargestDirectoriesFormatter,
    ) -> None:
        self._language_distribution_formatter = language_distribution_formatter
        self._commit_timeline_formatter = commit_timeline_formatter
        self._overview_cards_formatter = overview_cards_formatter
        self._health_gauge_formatter = health_gauge_formatter
        self._score_breakdown_formatter = score_breakdown_formatter
        self._repository_timeline_formatter = repository_timeline_formatter
        self._file_type_distribution_formatter = file_type_distribution_formatter
        self._largest_directories_formatter = largest_directories_formatter

    def build_dashboard(
        self,
        repository_metadata: RepositoryMetadata,
        static_analysis_result: StaticAnalysisResult,
        git_history_result: GitHistoryResult,
        repository_metrics_result: RepositoryMetricsResult,
    ) -> AnalyticsDashboardResult:
        """Build the complete chart-ready analytics dashboard payload."""
        logger.info("Building analytics dashboard for %s", repository_metadata.full_name)

        result = AnalyticsDashboardResult(
            language_distribution=self._language_distribution_formatter.format(static_analysis_result),
            commit_timeline=self._commit_timeline_formatter.format(git_history_result),
            overview_cards=self._overview_cards_formatter.format(
                repository_metadata, static_analysis_result, git_history_result, repository_metrics_result
            ),
            health_gauge=self._health_gauge_formatter.format(repository_metrics_result),
            score_breakdown=self._score_breakdown_formatter.format(repository_metrics_result),
            repository_timeline=self._repository_timeline_formatter.format(
                repository_metadata, git_history_result
            ),
            file_type_distribution=self._file_type_distribution_formatter.format(static_analysis_result),
            largest_directories=self._largest_directories_formatter.format(static_analysis_result),
            generated_at=datetime.now(timezone.utc),
        )

        logger.info("Completed analytics dashboard for %s", repository_metadata.full_name)
        return result
