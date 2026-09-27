"""
HealthGaugeFormatter — Module 6 component.

Wraps Module 5's already-computed overall health score into a
gauge-chart-ready shape. The only new element is a presentational status
band (Excellent/Good/Fair/Poor) used purely for gauge coloring in the
UI — it is not a new engineering metric, just a display-threshold label
applied to a score Module 5 already produced.
"""

import logging

from app.schemas.analytics import HealthGauge
from app.schemas.metrics import RepositoryMetricsResult

logger = logging.getLogger(__name__)


class HealthGaugeFormatter:
    """Formats Module 5's overall health score for gauge-chart consumption."""

    def __init__(
        self,
        excellent_threshold: float,
        good_threshold: float,
        fair_threshold: float,
    ) -> None:
        self._excellent_threshold = excellent_threshold
        self._good_threshold = good_threshold
        self._fair_threshold = fair_threshold

    def format(self, repository_metrics_result: RepositoryMetricsResult) -> HealthGauge:
        """Return a gauge-ready representation of the overall health score."""
        score = repository_metrics_result.overall_health_score.score
        status = self._status_band(score)
        logger.debug("Formatted health gauge: score=%.2f status=%s", score, status)
        return HealthGauge(value=score, min=0, max=100, label="Repository Health Score", status=status)

    def _status_band(self, score: float) -> str:
        if score >= self._excellent_threshold:
            return "Excellent"
        if score >= self._good_threshold:
            return "Good"
        if score >= self._fair_threshold:
            return "Fair"
        return "Poor"
