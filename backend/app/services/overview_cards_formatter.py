"""
OverviewCardsFormatter — Module 6 component.

Assembles a small set of headline KPI cards from values already present
in Modules 1, 3, 4, and 5's outputs — no new computation, just selection
and relabeling of existing fields.
"""

import logging
from typing import List

from app.schemas.analytics import OverviewCard
from app.schemas.git_history import GitHistoryResult
from app.schemas.metrics import RepositoryMetricsResult
from app.schemas.repository import RepositoryMetadata
from app.schemas.static_analysis import StaticAnalysisResult

logger = logging.getLogger(__name__)


class OverviewCardsFormatter:
    """Formats headline KPI cards for a repository dashboard overview strip."""

    def format(
        self,
        repository_metadata: RepositoryMetadata,
        static_analysis_result: StaticAnalysisResult,
        git_history_result: GitHistoryResult,
        repository_metrics_result: RepositoryMetricsResult,
    ) -> List[OverviewCard]:
        """Return a fixed set of overview cards drawn directly from upstream outputs."""
        cards = [
            OverviewCard(label="Stars", value=repository_metadata.stargazers_count, unit=None),
            OverviewCard(label="Forks", value=repository_metadata.forks_count, unit=None),
            OverviewCard(label="Watchers", value=repository_metadata.watchers_count, unit=None),
            OverviewCard(label="Open Issues", value=repository_metadata.open_issues_count, unit=None),
            OverviewCard(label="Contributors", value=git_history_result.unique_contributors, unit=None),
            OverviewCard(label="Total Commits", value=git_history_result.total_commits, unit=None),
            OverviewCard(label="Total Files", value=static_analysis_result.total_files, unit="files"),
            OverviewCard(label="Total Lines", value=static_analysis_result.total_lines, unit="lines"),
            OverviewCard(
                label="Overall Health Score",
                value=repository_metrics_result.overall_health_score.score,
                unit="/100",
            ),
        ]
        logger.debug("Formatted %d overview cards", len(cards))
        return cards
