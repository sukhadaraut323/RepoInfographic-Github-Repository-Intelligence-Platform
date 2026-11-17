"""
Service layer for Module 5 — Engineering Metrics Engine.

Orchestrates the five analyzers plus the health score calculator to
transform Modules 1, 3, and 4's structured outputs into
`RepositoryMetricsResult`. Performs no scanning, no git history reading,
and no GitHub API calls of its own — every input is data already
produced by earlier modules.
"""

import logging
from datetime import datetime, timezone

from app.schemas.git_history import GitHistoryResult
from app.schemas.metrics import RepositoryMetricsResult
from app.schemas.repository import RepositoryMetadata
from app.schemas.static_analysis import StaticAnalysisResult
from app.services.activity_analyzer import ActivityAnalyzer
from app.services.best_practices_analyzer import BestPracticesAnalyzer
from app.services.codebase_analyzer import CodebaseAnalyzer
from app.services.community_analyzer import CommunityAnalyzer
from app.services.documentation_analyzer import DocumentationAnalyzer
from app.services.health_score_calculator import HealthScoreCalculator

logger = logging.getLogger(__name__)


class RepositoryMetricsService:
    """Computes explainable engineering metrics and the overall health score."""

    def __init__(
        self,
        documentation_analyzer: DocumentationAnalyzer,
        codebase_analyzer: CodebaseAnalyzer,
        activity_analyzer: ActivityAnalyzer,
        community_analyzer: CommunityAnalyzer,
        best_practices_analyzer: BestPracticesAnalyzer,
        health_score_calculator: HealthScoreCalculator,
    ) -> None:
        self._documentation_analyzer = documentation_analyzer
        self._codebase_analyzer = codebase_analyzer
        self._activity_analyzer = activity_analyzer
        self._community_analyzer = community_analyzer
        self._best_practices_analyzer = best_practices_analyzer
        self._health_score_calculator = health_score_calculator

    def compute_metrics(
        self,
        repository_metadata: RepositoryMetadata,
        static_analysis_result: StaticAnalysisResult,
        git_history_result: GitHistoryResult,
    ) -> RepositoryMetricsResult:
        """
        Compute all six sub-scores plus the overall health score.

        Args:
            repository_metadata: Output of Module 1.
            static_analysis_result: Output of Module 3.
            git_history_result: Output of Module 4.

        Returns:
            A populated `RepositoryMetricsResult`.
        """
        logger.info("Computing engineering metrics for %s", repository_metadata.full_name)

        documentation_score = self._documentation_analyzer.analyze(static_analysis_result)
        codebase_score = self._codebase_analyzer.analyze_codebase(static_analysis_result)
        maintainability_score = self._codebase_analyzer.analyze_maintainability(static_analysis_result)
        activity_score = self._activity_analyzer.analyze(git_history_result)
        community_score = self._community_analyzer.analyze(repository_metadata, git_history_result)
        best_practices_score = self._best_practices_analyzer.analyze(static_analysis_result)

        overall_health_score = self._health_score_calculator.calculate_overall_score(
            documentation_score=documentation_score,
            codebase_score=codebase_score,
            activity_score=activity_score,
            community_score=community_score,
            maintainability_score=maintainability_score,
            best_practices_score=best_practices_score,
        )

        result = RepositoryMetricsResult(
            documentation_score=documentation_score,
            codebase_score=codebase_score,
            activity_score=activity_score,
            community_score=community_score,
            maintainability_score=maintainability_score,
            best_practices_score=best_practices_score,
            overall_health_score=overall_health_score,
            calculated_at=datetime.now(timezone.utc),
        )

        logger.info(
            "Completed engineering metrics for %s: overall health score %.2f",
            repository_metadata.full_name,
            overall_health_score.score,
        )
        return result
