"""
HealthScoreCalculator — Module 5 component.

Responsible ONLY for combining the six already-computed sub-scores into
the Overall Repository Health Score via a weighted average. It performs
no evidence gathering or analysis of its own — that is each analyzer's
responsibility.
"""

import logging
from typing import List

from app.schemas.metrics import SubScore

logger = logging.getLogger(__name__)


class HealthScoreCalculator:
    """Combines Documentation/Codebase/Activity/Community/Maintainability/BestPractices scores."""

    def __init__(
        self,
        weight_documentation: float,
        weight_codebase: float,
        weight_activity: float,
        weight_community: float,
        weight_maintainability: float,
        weight_best_practices: float,
    ) -> None:
        self._weights = {
            "Documentation": weight_documentation,
            "Codebase": weight_codebase,
            "Activity": weight_activity,
            "Community": weight_community,
            "Maintainability": weight_maintainability,
            "Best Practices": weight_best_practices,
        }

    def calculate_overall_score(
        self,
        documentation_score: SubScore,
        codebase_score: SubScore,
        activity_score: SubScore,
        community_score: SubScore,
        maintainability_score: SubScore,
        best_practices_score: SubScore,
    ) -> SubScore:
        """Combine the six sub-scores into a single weighted overall score."""
        scores_by_name = {
            "Documentation": documentation_score,
            "Codebase": codebase_score,
            "Activity": activity_score,
            "Community": community_score,
            "Maintainability": maintainability_score,
            "Best Practices": best_practices_score,
        }

        overall = sum(
            scores_by_name[name].score * weight for name, weight in self._weights.items()
        )

        evidence: List[str] = [
            f"{name} score: {scores_by_name[name].score:.2f}/100 (weight {weight * 100:.0f}%)."
            for name, weight in self._weights.items()
        ]

        reasons: List[str] = self._build_reasons(scores_by_name)

        logger.debug("Overall health score computed: %.2f", overall)
        return SubScore(score=round(min(max(overall, 0.0), 100.0), 2), evidence=evidence, reasons=reasons)

    @staticmethod
    def _build_reasons(scores_by_name: dict) -> List[str]:
        """Call out the sub-scores that most significantly help or hurt the overall score."""
        reasons: List[str] = []
        for name, sub_score in scores_by_name.items():
            if sub_score.score < 40:
                reasons.append(f"{name} score is low ({sub_score.score:.0f}/100), significantly reducing overall health.")
            elif sub_score.score >= 85:
                reasons.append(f"{name} score is strong ({sub_score.score:.0f}/100), boosting overall health.")
        return reasons
