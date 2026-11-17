"""Unit tests for app.services.commit_timeline_formatter.CommitTimelineFormatter."""

from app.core.config import get_settings
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


def test_production_default_keeps_a_35_month_history_monthly_not_yearly() -> None:
    """
    Regression test for the month-wise requirement: a repository spanning
    just under 3 years (35 raw monthly points, matching a real repository
    used during manual verification) must retain monthly granularity under
    the actual production-wired default (Settings, not the formatter
    class's own standalone default), not collapse to yearly.
    """
    formatter = CommitTimelineFormatter(monthly_point_limit=get_settings().analytics_commit_timeline_monthly_point_limit)
    monthly = [MonthlyCommitCount(month=f"2023-{m:02d}", commit_count=1) for m in range(1, 13)]
    monthly += [MonthlyCommitCount(month=f"2024-{m:02d}", commit_count=1) for m in range(1, 13)]
    monthly += [MonthlyCommitCount(month=f"2025-{m:02d}", commit_count=1) for m in range(1, 12)]
    assert len(monthly) == 35
    result = make_git_history_result().model_copy(update={"monthly_commit_timeline": monthly})

    points = formatter.format(result)

    assert len(points) == 35
    assert points[0].month == "2023-01" and points[-1].month == "2025-11"


def test_timeline_at_or_under_the_point_limit_stays_monthly() -> None:
    formatter = CommitTimelineFormatter(monthly_point_limit=3)
    result = make_git_history_result().model_copy(
        update={
            "monthly_commit_timeline": [
                MonthlyCommitCount(month="2024-01", commit_count=1),
                MonthlyCommitCount(month="2024-02", commit_count=0),
                MonthlyCommitCount(month="2024-03", commit_count=2),
            ]
        }
    )

    points = formatter.format(result)

    assert [p.month for p in points] == ["2024-01", "2024-02", "2024-03"]


def test_sparse_long_history_above_the_limit_aggregates_by_year_without_losing_commits() -> None:
    """
    Regression test for the real bug found via octocat/Hello-World: 5 real
    commits spread across many years produced dozens of zero-filled months
    that made the chart look empty. Aggregating by year keeps every real
    commit counted while staying visually readable.
    """
    formatter = CommitTimelineFormatter(monthly_point_limit=24)
    monthly = [MonthlyCommitCount(month=f"2010-{m:02d}", commit_count=0) for m in range(1, 13)]
    monthly += [MonthlyCommitCount(month="2011-01", commit_count=1)]
    monthly += [MonthlyCommitCount(month=f"2011-{m:02d}", commit_count=0) for m in range(2, 13)]
    monthly += [MonthlyCommitCount(month=f"2012-{m:02d}", commit_count=0) for m in range(1, 6)]
    monthly += [MonthlyCommitCount(month="2012-06", commit_count=2)]
    monthly += [MonthlyCommitCount(month=f"2012-{m:02d}", commit_count=0) for m in range(7, 13)]
    result = make_git_history_result().model_copy(update={"monthly_commit_timeline": monthly})
    assert len(monthly) > 24  # confirms this test actually exercises the aggregation path

    points = formatter.format(result)

    assert [p.month for p in points] == ["2010", "2011", "2012"]
    by_year = {p.month: p.commits for p in points}
    assert by_year == {"2010": 0, "2011": 1, "2012": 2}
    assert sum(by_year.values()) == sum(m.commit_count for m in monthly)  # no commits lost
