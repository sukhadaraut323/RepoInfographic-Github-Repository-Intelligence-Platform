"""Unit tests for app.services.repository_timeline_formatter.RepositoryTimelineFormatter."""

from datetime import datetime, timezone

from app.services.repository_timeline_formatter import RepositoryTimelineFormatter
from app.tests.factories import make_git_history_result, make_repository_metadata

FORMATTER = RepositoryTimelineFormatter()


def test_returns_all_four_events_sorted_chronologically() -> None:
    metadata = make_repository_metadata()
    metadata = metadata.model_copy(
        update={
            "created_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "pushed_at": datetime(2024, 6, 1, tzinfo=timezone.utc),
        }
    )
    history = make_git_history_result()
    history = history.model_copy(
        update={
            "first_commit_date": datetime(2020, 2, 1, tzinfo=timezone.utc),
            "latest_commit_date": datetime(2024, 5, 1, tzinfo=timezone.utc),
        }
    )

    events = FORMATTER.format(metadata, history)

    assert len(events) == 4
    labels_in_order = [event.label for event in events]
    assert labels_in_order == ["Repository Created", "First Commit", "Latest Commit", "Last Push"]


def test_skips_none_commit_dates_for_empty_repo() -> None:
    metadata = make_repository_metadata()
    history = make_git_history_result()
    history = history.model_copy(update={"first_commit_date": None, "latest_commit_date": None})

    events = FORMATTER.format(metadata, history)

    labels = {event.label for event in events}
    assert "First Commit" not in labels
    assert "Latest Commit" not in labels
    assert "Repository Created" in labels
