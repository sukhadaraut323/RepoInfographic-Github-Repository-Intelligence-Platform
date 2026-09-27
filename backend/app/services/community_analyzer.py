"""
CommunityAnalyzer — Module 5 component.

Scores community engagement from Module 1's `RepositoryMetadata` (stars,
forks, watchers, open issues). Unique contributor count is not exposed
by Module 1, so it is sourced from Module 4's `GitHistoryResult`
(`unique_contributors`) — this is still consuming an existing structured
output rather than recomputing anything, just from a different upstream
module than the rest of this analyzer's inputs.
"""

import logging
from typing import List

from app.schemas.git_history import GitHistoryResult
from app.schemas.metrics import SubScore
from app.schemas.repository import RepositoryMetadata

logger = logging.getLogger(__name__)

# --- Weights (sum to 100) ---
_STARS_WEIGHT = 30
_FORKS_WEIGHT = 20
_CONTRIBUTORS_WEIGHT = 20
_WATCHERS_WEIGHT = 15
_OPEN_ISSUES_WEIGHT = 15


class CommunityAnalyzer:
    """Computes the Community Score from Module 1's metadata and Module 4's contributor count."""

    def analyze(
        self, repository_metadata: RepositoryMetadata, git_history_result: GitHistoryResult
    ) -> SubScore:
        """Score community engagement (0-100) with evidence and reasons."""
        evidence: List[str] = []
        reasons: List[str] = []
        score = 0.0

        stars_points = self._tiered_points(
            repository_metadata.stargazers_count, _STARS_WEIGHT, thresholds=(1000, 100, 10, 1)
        )
        score += stars_points
        evidence.append(f"{repository_metadata.stargazers_count} stars.")
        if stars_points < _STARS_WEIGHT:
            reasons.append(f"Low star count (-{_STARS_WEIGHT - stars_points:.0f} pts).")

        forks_points = self._tiered_points(
            repository_metadata.forks_count, _FORKS_WEIGHT, thresholds=(100, 10, 1)
        )
        score += forks_points
        evidence.append(f"{repository_metadata.forks_count} forks.")
        if forks_points < _FORKS_WEIGHT:
            reasons.append(f"Low fork count (-{_FORKS_WEIGHT - forks_points:.0f} pts).")

        contributors_points = self._tiered_points(
            git_history_result.unique_contributors, _CONTRIBUTORS_WEIGHT, thresholds=(10, 3, 1)
        )
        score += contributors_points
        evidence.append(f"{git_history_result.unique_contributors} unique contributor(s).")
        if contributors_points < _CONTRIBUTORS_WEIGHT:
            reasons.append(f"Few unique contributors (-{_CONTRIBUTORS_WEIGHT - contributors_points:.0f} pts).")

        watchers_points = self._tiered_points(
            repository_metadata.watchers_count, _WATCHERS_WEIGHT, thresholds=(100, 10, 1)
        )
        score += watchers_points
        evidence.append(f"{repository_metadata.watchers_count} watchers.")
        if watchers_points < _WATCHERS_WEIGHT:
            reasons.append(f"Low watcher count (-{_WATCHERS_WEIGHT - watchers_points:.0f} pts).")

        if repository_metadata.open_issues_count >= 1:
            score += _OPEN_ISSUES_WEIGHT
            evidence.append(
                f"{repository_metadata.open_issues_count} open issues (indicates active engagement)."
            )
        else:
            evidence.append("No open issues recorded.")
            reasons.append(f"No open issues indicating active engagement (-{_OPEN_ISSUES_WEIGHT} pts).")

        logger.debug("Community score computed: %.2f", score)
        return SubScore(score=round(min(score, 100.0), 2), evidence=evidence, reasons=reasons)

    @staticmethod
    def _tiered_points(value: int, weight: float, thresholds: tuple) -> float:
        """
        Award points on a tiered scale: the highest threshold met gets the
        full weight, each lower threshold gets a proportionally smaller share.
        `thresholds` must be given in descending order.
        """
        tier_count = len(thresholds)
        for index, threshold in enumerate(thresholds):
            if value >= threshold:
                return weight * ((tier_count - index) / tier_count)
        return 0.0
