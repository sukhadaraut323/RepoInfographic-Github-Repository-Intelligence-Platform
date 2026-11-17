"""
RepositoryTimelineFormatter — Module 6 component.

Assembles a small set of dated milestone events (repository created,
first commit, latest commit, last push) from fields already present in
Modules 1 and 4's outputs. Distinct from the Commit Timeline (a monthly
commit-count histogram) — this is a discrete event timeline for a
timeline/milestone chart widget.
"""

import logging
from typing import List

from app.schemas.analytics import RepositoryTimelineEvent
from app.schemas.git_history import GitHistoryResult
from app.schemas.repository import RepositoryMetadata

logger = logging.getLogger(__name__)


class RepositoryTimelineFormatter:
    """Formats key dated milestones from Module 1 and Module 4 outputs."""

    def format(
        self, repository_metadata: RepositoryMetadata, git_history_result: GitHistoryResult
    ) -> List[RepositoryTimelineEvent]:
        """Return chronologically-sorted milestone events, skipping any that are absent."""
        candidate_events = [
            (repository_metadata.created_at, "Repository Created"),
            (git_history_result.first_commit_date, "First Commit"),
            (git_history_result.latest_commit_date, "Latest Commit"),
            (repository_metadata.pushed_at, "Last Push"),
        ]

        events = [
            RepositoryTimelineEvent(date=date, label=label)
            for date, label in candidate_events
            if date is not None
        ]
        events.sort(key=lambda event: event.date)

        logger.debug("Formatted %d repository timeline events", len(events))
        return events
