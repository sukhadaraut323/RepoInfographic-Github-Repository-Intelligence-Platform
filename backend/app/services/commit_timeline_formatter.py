"""
CommitTimelineFormatter — Module 6 component.

Reshapes Module 4's `monthly_commit_timeline` (already gap-filled and
computed) into a Recharts-ready line/bar chart shape. No new date
bucketing or counting happens here — only field renaming.
"""

import logging
from typing import List

from app.schemas.analytics import CommitTimelinePoint
from app.schemas.git_history import GitHistoryResult

logger = logging.getLogger(__name__)


class CommitTimelineFormatter:
    """Formats Module 4's monthly commit timeline for chart consumption."""

    def format(self, git_history_result: GitHistoryResult) -> List[CommitTimelinePoint]:
        """Return chart-ready monthly commit points, already ordered by Module 4."""
        points = [
            CommitTimelinePoint(month=entry.month, commits=entry.commit_count)
            for entry in git_history_result.monthly_commit_timeline
        ]
        logger.debug("Formatted %d commit timeline points", len(points))
        return points
