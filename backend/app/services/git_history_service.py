"""
Service layer for Module 4 — Git History Analysis.

Orchestrates:
    1. `GitHistoryAnalyzer` — opens the repository and extracts raw commit
       and branch metadata.
    2. Simple arithmetic over that raw data (averages, monthly timeline,
       activity classification) to assemble `GitHistoryResult`.

No blame, release, merge, or code-ownership analysis happens here — only
counts and averages derived directly from commit timestamps and authors.
"""

import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.schemas.git_history import ActivityLevel, GitHistoryResult, MonthlyCommitCount
from app.services.git_history_analyzer import CommitInfo, GitHistoryAnalyzer

logger = logging.getLogger(__name__)

_AVERAGE_DAYS_PER_MONTH = 30.44


class GitHistoryService:
    """Produces structured engineering history for a locally cloned repository."""

    def __init__(
        self,
        analyzer: GitHistoryAnalyzer,
        activity_window_days: int,
        high_activity_threshold: int,
        medium_activity_threshold: int,
        low_activity_threshold: int,
    ) -> None:
        self._analyzer = analyzer
        self._activity_window_days = activity_window_days
        self._high_activity_threshold = high_activity_threshold
        self._medium_activity_threshold = medium_activity_threshold
        self._low_activity_threshold = low_activity_threshold

    def analyze(self, local_path: str) -> GitHistoryResult:
        """
        Analyze the git history of the repository at `local_path`.

        Raises:
            RepositoryPathNotFoundError: If `local_path` does not exist or
                is not a directory.
            NotAGitRepositoryError: If `local_path` is not a valid git repository.
            GitHistoryAnalysisError: If commit/branch metadata cannot be read.
        """
        root = Path(local_path)
        logger.info("Starting git history analysis for %s", root)

        repo = self._analyzer.open_repository(root)
        commits = self._analyzer.get_commits(repo)
        branch_names = self._analyzer.get_branch_names(repo)
        default_branch = self._analyzer.get_default_branch(repo, branch_names)

        now = datetime.now(timezone.utc)

        if not commits:
            result = GitHistoryResult(
                local_path=str(root),
                repository_age_days=0,
                first_commit_date=None,
                latest_commit_date=None,
                total_commits=0,
                unique_contributors=0,
                total_branches=len(branch_names),
                default_branch=default_branch,
                average_commits_per_day=0.0,
                average_commits_per_week=0.0,
                average_commits_per_month=0.0,
                monthly_commit_timeline=[],
                recent_activity_level=ActivityLevel.DORMANT,
                analyzed_at=now,
            )
            logger.info("Repository at %s has no commits; returning empty history.", root)
            return result

        sorted_commits = sorted(commits, key=lambda c: c.committed_datetime)
        first_commit_date = sorted_commits[0].committed_datetime
        latest_commit_date = sorted_commits[-1].committed_datetime

        repository_age_days = max((now - first_commit_date).days, 0)
        total_commits = len(commits)

        average_commits_per_day = self._safe_divide(total_commits, max(repository_age_days, 1))
        average_commits_per_week = round(average_commits_per_day * 7, 2)
        average_commits_per_month = round(average_commits_per_day * _AVERAGE_DAYS_PER_MONTH, 2)

        unique_contributors = len({commit.author_email for commit in commits})
        monthly_timeline = self._build_monthly_timeline(sorted_commits)
        activity_level = self._classify_activity(commits, now)

        result = GitHistoryResult(
            local_path=str(root),
            repository_age_days=repository_age_days,
            first_commit_date=first_commit_date,
            latest_commit_date=latest_commit_date,
            total_commits=total_commits,
            unique_contributors=unique_contributors,
            total_branches=len(branch_names),
            default_branch=default_branch,
            average_commits_per_day=round(average_commits_per_day, 2),
            average_commits_per_week=average_commits_per_week,
            average_commits_per_month=average_commits_per_month,
            monthly_commit_timeline=monthly_timeline,
            recent_activity_level=activity_level,
            analyzed_at=now,
        )

        logger.info(
            "Completed git history analysis for %s: %d commits, %d contributors, activity=%s",
            root,
            total_commits,
            unique_contributors,
            activity_level.value,
        )
        return result

    @staticmethod
    def _safe_divide(numerator: float, denominator: float) -> float:
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def _build_monthly_timeline(sorted_commits: List[CommitInfo]) -> List[MonthlyCommitCount]:
        """
        Build a commit-count-per-month timeline spanning from the first to
        the latest commit's month, inclusive, filling any inactive months
        with zero so the timeline is continuous (chart-ready).
        """
        counts = Counter(commit.committed_datetime.strftime("%Y-%m") for commit in sorted_commits)

        first_month = sorted_commits[0].committed_datetime.replace(day=1)
        last_month = sorted_commits[-1].committed_datetime.replace(day=1)

        timeline: List[MonthlyCommitCount] = []
        cursor = first_month
        while cursor <= last_month:
            key = cursor.strftime("%Y-%m")
            timeline.append(MonthlyCommitCount(month=key, commit_count=counts.get(key, 0)))
            # Advance to the first day of the next month.
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year + 1, month=1)
            else:
                cursor = cursor.replace(month=cursor.month + 1)

        return timeline

    def _classify_activity(self, commits: List[CommitInfo], now: datetime) -> ActivityLevel:
        """Classify recent activity based on commit count within the configured window."""
        window_start = now.timestamp() - (self._activity_window_days * 86400)
        recent_commit_count = sum(
            1 for commit in commits if commit.committed_datetime.timestamp() >= window_start
        )

        if recent_commit_count >= self._high_activity_threshold:
            return ActivityLevel.HIGH
        if recent_commit_count >= self._medium_activity_threshold:
            return ActivityLevel.MEDIUM
        if recent_commit_count >= self._low_activity_threshold:
            return ActivityLevel.LOW
        return ActivityLevel.DORMANT
