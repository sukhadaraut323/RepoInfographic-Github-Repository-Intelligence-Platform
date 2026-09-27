"""Unit tests for app.services.commit_timeline_formatter.CommitTimelineFormatter."""

from app.schemas.git_history import MonthlyCommitCount
from app.services.commit_timeline_formatter import CommitTimelineFormatter
from app.tests.factories import make_git_history_result

FORMATTER = CommitTimelineFormatter()


def test_formats_monthly_commits_to_chart_points() -> None:
    result = make_git_history_result()
    result = result.model_copy(
        update={
            "monthly_commit_timeline": [
                MonthlyCommitCount(month="2024-01", commit_count=5),
                MonthlyCommitCount(month="2024-02", commit_count=10),
            ]
        }
    )

    points = FORMATTER.format(result)

    assert len(points) == 2
    assert points[0].month == "2024-01"
    assert points[0].commits == 5
    assert points[1].commits == 10


def test_empty_timeline_returns_empty_list() -> None:
    result = make_git_history_result()

    points = FORMATTER.format(result)

    assert points == []
