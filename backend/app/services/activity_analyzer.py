"""
ActivityAnalyzer — Module 5 component.

Scores repository activity entirely from Module 4's `GitHistoryResult` —
no re-reading of git history happens here.
"""

import logging
from typing import List

from app.schemas.git_history import ActivityLevel, GitHistoryResult
from app.schemas.metrics import SubScore

logger = logging.getLogger(__name__)

# --- Weights (sum to 100) ---
_RECENT_ACTIVITY_WEIGHT = 40
_COMMIT_FREQUENCY_WEIGHT = 30
_CONTRIBUTOR_COUNT_WEIGHT = 20
_REPOSITORY_AGE_WEIGHT = 10

_RECENT_ACTIVITY_POINTS = {
    ActivityLevel.HIGH: _RECENT_ACTIVITY_WEIGHT,
    ActivityLevel.MEDIUM: _RECENT_ACTIVITY_WEIGHT * 0.625,  # 25/40
    ActivityLevel.LOW: _RECENT_ACTIVITY_WEIGHT * 0.25,  # 10/40
    ActivityLevel.DORMANT: 0.0,
}

_ESTABLISHED_REPOSITORY_AGE_DAYS = 365


class ActivityAnalyzer:
    """Computes the Activity Score from Module 4's git history output."""

    def analyze(self, git_history_result: GitHistoryResult) -> SubScore:
        """Score repository activity (0-100) with evidence and reasons."""
        evidence: List[str] = []
        reasons: List[str] = []
        score = 0.0

        activity_points = _RECENT_ACTIVITY_POINTS[git_history_result.recent_activity_level]
        score += activity_points
        evidence.append(f"Recent activity level: {git_history_result.recent_activity_level.value}.")
        if activity_points < _RECENT_ACTIVITY_WEIGHT:
            reasons.append(
                f"Recent activity level is '{git_history_result.recent_activity_level.value}' "
                f"(-{_RECENT_ACTIVITY_WEIGHT - activity_points:.0f} pts)."
            )

        commit_frequency_points = self._commit_frequency_points(git_history_result.average_commits_per_month)
        score += commit_frequency_points
        evidence.append(
            f"Average commit frequency: {git_history_result.average_commits_per_month:.2f} commits/month."
        )
        if commit_frequency_points < _COMMIT_FREQUENCY_WEIGHT:
            reasons.append(
                f"Low commit frequency (-{_COMMIT_FREQUENCY_WEIGHT - commit_frequency_points:.0f} pts)."
            )

        contributor_points = self._contributor_points(git_history_result.unique_contributors)
        score += contributor_points
        evidence.append(f"{git_history_result.unique_contributors} unique contributor(s).")
        if contributor_points < _CONTRIBUTOR_COUNT_WEIGHT:
            reasons.append(
                f"Few unique contributors (-{_CONTRIBUTOR_COUNT_WEIGHT - contributor_points:.0f} pts)."
            )

        if git_history_result.repository_age_days >= _ESTABLISHED_REPOSITORY_AGE_DAYS:
            score += _REPOSITORY_AGE_WEIGHT
            evidence.append(f"Repository age: {git_history_result.repository_age_days} days (established).")
        else:
            partial = _REPOSITORY_AGE_WEIGHT * (
                git_history_result.repository_age_days / _ESTABLISHED_REPOSITORY_AGE_DAYS
            )
            score += partial
            evidence.append(f"Repository age: {git_history_result.repository_age_days} days (young).")
            reasons.append(f"Repository is less than a year old (-{_REPOSITORY_AGE_WEIGHT - partial:.0f} pts).")

        logger.debug("Activity score computed: %.2f", score)
        return SubScore(score=round(min(score, 100.0), 2), evidence=evidence, reasons=reasons)

    @staticmethod
    def _commit_frequency_points(average_commits_per_month: float) -> float:
        if average_commits_per_month >= 20:
            return _COMMIT_FREQUENCY_WEIGHT
        if average_commits_per_month >= 5:
            return _COMMIT_FREQUENCY_WEIGHT * (20 / 30)  # ~20 pts
        if average_commits_per_month >= 1:
            return _COMMIT_FREQUENCY_WEIGHT * (10 / 30)  # ~10 pts
        return 0.0

    @staticmethod
    def _contributor_points(unique_contributors: int) -> float:
        if unique_contributors >= 10:
            return _CONTRIBUTOR_COUNT_WEIGHT
        if unique_contributors >= 3:
            return _CONTRIBUTOR_COUNT_WEIGHT * 0.6
        if unique_contributors >= 1:
            return _CONTRIBUTOR_COUNT_WEIGHT * 0.25
        return 0.0
