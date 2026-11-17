"""
CommitTimelineFormatter — Module 6 component.

Reshapes Module 4's `monthly_commit_timeline` (already gap-filled and
computed) into a Recharts-ready line/bar chart shape.

Module 4's timeline is zero-filled for *every* calendar month between a
repository's first and last commit, so it stays mathematically continuous.
For a repository with a long history but sparse activity (e.g. 5 commits
spread across 7 years), that produces dozens of near-entirely-zero months
that visually drown out the handful of real data points, making the chart
look empty at a glance even though real commits exist.

Above `monthly_point_limit`, this formatter aggregates the same real counts
into one point per calendar year instead, so a long sparse history still
renders as a readable chart. No commit counts are invented or dropped —
every commit is still counted, just bucketed more coarsely. Below the
limit, the monthly granularity is unchanged.
"""

import logging
from collections import OrderedDict
from typing import List

from app.schemas.analytics import CommitTimelinePoint
from app.schemas.git_history import GitHistoryResult

logger = logging.getLogger(__name__)


class CommitTimelineFormatter:
    """Formats Module 4's monthly commit timeline for chart consumption."""

    def __init__(self, monthly_point_limit: int = 24) -> None:
        self._monthly_point_limit = monthly_point_limit

    def format(self, git_history_result: GitHistoryResult) -> List[CommitTimelinePoint]:
        """Return chart-ready commit timeline points, ordered chronologically."""
        monthly = git_history_result.monthly_commit_timeline

        if len(monthly) <= self._monthly_point_limit:
            points = [CommitTimelinePoint(month=entry.month, commits=entry.commit_count) for entry in monthly]
            logger.debug("Formatted %d monthly commit timeline points", len(points))
            return points

        yearly: "OrderedDict[str, int]" = OrderedDict()
        for entry in monthly:
            year = entry.month.split("-", 1)[0]
            yearly[year] = yearly.get(year, 0) + entry.commit_count

        points = [CommitTimelinePoint(month=year, commits=count) for year, count in yearly.items()]
        logger.debug(
            "Aggregated %d sparse monthly points into %d yearly commit timeline points", len(monthly), len(points)
        )
        return points
