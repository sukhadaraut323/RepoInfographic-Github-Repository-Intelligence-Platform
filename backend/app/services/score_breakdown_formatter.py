"""
ScoreBreakdownFormatter — Module 6 component.

Reshapes Module 5's six sub-scores into a Recharts-ready bar/radar chart
shape. No score computation happens here — only selection and relabeling
of Module 5's already-computed `SubScore.score` values.
"""

import logging
from typing import List

from app.schemas.analytics import ScoreBreakdownEntry
from app.schemas.metrics import RepositoryMetricsResult

logger = logging.getLogger(__name__)


class ScoreBreakdownFormatter:
    """Formats Module 5's six sub-scores for bar/radar chart consumption."""

    def format(self, repository_metrics_result: RepositoryMetricsResult) -> List[ScoreBreakdownEntry]:
        """Return the six sub-scores as chart-ready category/score entries."""
        entries = [
            ScoreBreakdownEntry(category="Documentation", score=repository_metrics_result.documentation_score.score),
            ScoreBreakdownEntry(category="Codebase", score=repository_metrics_result.codebase_score.score),
            ScoreBreakdownEntry(category="Activity", score=repository_metrics_result.activity_score.score),
            ScoreBreakdownEntry(category="Community", score=repository_metrics_result.community_score.score),
            ScoreBreakdownEntry(
                category="Maintainability", score=repository_metrics_result.maintainability_score.score
            ),
            ScoreBreakdownEntry(
                category="Best Practices", score=repository_metrics_result.best_practices_score.score
            ),
        ]
        logger.debug("Formatted %d score breakdown entries", len(entries))
        return entries
