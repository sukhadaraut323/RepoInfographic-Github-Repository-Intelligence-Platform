"""Unit tests for app.services.git_history_service.GitHistoryService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.schemas.git_history import ActivityLevel
from app.services.git_history_analyzer import CommitInfo
from app.services.git_history_service import GitHistoryService


def _commit(days_ago: int, email: str = "dev@example.com") -> CommitInfo:
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return CommitInfo(sha=f"sha-{days_ago}", author_name="Dev", author_email=email, committed_datetime=when)


@pytest.fixture
def mock_analyzer() -> MagicMock:
    return MagicMock()


def _make_service(mock_analyzer, **overrides) -> GitHistoryService:
    defaults = dict(
        activity_window_days=30,
        high_activity_threshold=20,
        medium_activity_threshold=5,
        low_activity_threshold=1,
    )
    defaults.update(overrides)
    return GitHistoryService(analyzer=mock_analyzer, **defaults)


def test_analyze_empty_repository_returns_zeroed_result(mock_analyzer, tmp_path) -> None:
    mock_analyzer.open_repository.return_value = MagicMock()
    mock_analyzer.get_commits.return_value = []
    mock_analyzer.get_branch_names.return_value = []
    mock_analyzer.get_default_branch.return_value = None

    service = _make_service(mock_analyzer)
    result = service.analyze(str(tmp_path))

    assert result.total_commits == 0
    assert result.unique_contributors == 0
    assert result.repository_age_days == 0
    assert result.first_commit_date is None
    assert result.latest_commit_date is None
    assert result.average_commits_per_day == 0.0
    assert result.monthly_commit_timeline == []
    assert result.recent_activity_level == ActivityLevel.DORMANT


def test_analyze_computes_unique_contributors(mock_analyzer, tmp_path) -> None:
    commits = [
        _commit(1, "alice@example.com"),
        _commit(2, "bob@example.com"),
        _commit(3, "alice@example.com"),
    ]
    mock_analyzer.open_repository.return_value = MagicMock()
    mock_analyzer.get_commits.return_value = commits
    mock_analyzer.get_branch_names.return_value = ["main"]
    mock_analyzer.get_default_branch.return_value = "main"

    service = _make_service(mock_analyzer)
    result = service.analyze(str(tmp_path))

    assert result.total_commits == 3
    assert result.unique_contributors == 2


def test_analyze_computes_repository_age_and_averages(mock_analyzer, tmp_path) -> None:
    commits = [_commit(days_ago=d) for d in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]]
    mock_analyzer.open_repository.return_value = MagicMock()
    mock_analyzer.get_commits.return_value = commits
    mock_analyzer.get_branch_names.return_value = ["main"]
    mock_analyzer.get_default_branch.return_value = "main"

    service = _make_service(mock_analyzer)
    result = service.analyze(str(tmp_path))

    assert result.repository_age_days in (89, 90, 91)  # tolerate timing jitter
    assert result.total_commits == 10
    assert result.average_commits_per_day > 0
    # Each average is independently rounded from the unrounded daily rate,
    # so allow a small absolute tolerance rather than requiring an exact
    # cross-multiplication of the already-rounded fields.
    assert result.average_commits_per_week == pytest.approx(result.average_commits_per_day * 7, abs=0.05)


def test_activity_level_high_when_many_recent_commits(mock_analyzer, tmp_path) -> None:
    commits = [_commit(days_ago=d % 5) for d in range(25)]  # 25 commits within last 5 days
    mock_analyzer.open_repository.return_value = MagicMock()
    mock_analyzer.get_commits.return_value = commits
    mock_analyzer.get_branch_names.return_value = ["main"]
    mock_analyzer.get_default_branch.return_value = "main"

    service = _make_service(mock_analyzer, high_activity_threshold=20)
    result = service.analyze(str(tmp_path))

    assert result.recent_activity_level == ActivityLevel.HIGH


def test_activity_level_dormant_when_no_recent_commits(mock_analyzer, tmp_path) -> None:
    commits = [_commit(days_ago=400)]  # long ago, outside default 30-day window
    mock_analyzer.open_repository.return_value = MagicMock()
    mock_analyzer.get_commits.return_value = commits
    mock_analyzer.get_branch_names.return_value = ["main"]
    mock_analyzer.get_default_branch.return_value = "main"

    service = _make_service(mock_analyzer)
    result = service.analyze(str(tmp_path))

    assert result.recent_activity_level == ActivityLevel.DORMANT


def test_monthly_timeline_fills_gaps_between_first_and_last_commit(mock_analyzer, tmp_path) -> None:
    now = datetime.now(timezone.utc)
    first = now - timedelta(days=95)  # roughly 3 months ago
    last = now - timedelta(days=1)
    commits = [
        CommitInfo(sha="a", author_name="Dev", author_email="d@example.com", committed_datetime=first),
        CommitInfo(sha="b", author_name="Dev", author_email="d@example.com", committed_datetime=last),
    ]
    mock_analyzer.open_repository.return_value = MagicMock()
    mock_analyzer.get_commits.return_value = commits
    mock_analyzer.get_branch_names.return_value = ["main"]
    mock_analyzer.get_default_branch.return_value = "main"

    service = _make_service(mock_analyzer)
    result = service.analyze(str(tmp_path))

    months = [entry.month for entry in result.monthly_commit_timeline]
    assert months == sorted(months)
    assert len(months) == len(set(months))  # no duplicate months
    assert len(result.monthly_commit_timeline) >= 3  # spans at least 3 calendar months


def test_monthly_timeline_includes_the_latest_commits_month_across_timezones(mock_analyzer, tmp_path) -> None:
    """
    Regression test for a real bug found via octocat/Hello-World: comparing
    `.replace(day=1)` datetimes directly (rather than plain year/month)
    converts both sides to UTC for comparison. When the first and last
    commits carry different UTC offsets, that can push the loop's cursor
    past the last commit's month in UTC terms and silently drop it - even
    though `sum(monthly_commit_timeline) == total_commits` should always
    hold. Here the first commit is UTC-08:00 and the last is UTC-05:00,
    reproducing the exact condition that previously dropped May 2018.
    """
    first = datetime(2011, 1, 26, 11, 6, 8, tzinfo=timezone(timedelta(hours=-8)))
    last = datetime(2018, 5, 10, 12, 55, 19, tzinfo=timezone(timedelta(hours=-5)))
    commits = [
        CommitInfo(sha="a", author_name="Dev", author_email="d@example.com", committed_datetime=first),
        CommitInfo(sha="b", author_name="Dev", author_email="d@example.com", committed_datetime=last),
    ]
    mock_analyzer.open_repository.return_value = MagicMock()
    mock_analyzer.get_commits.return_value = commits
    mock_analyzer.get_branch_names.return_value = ["main"]
    mock_analyzer.get_default_branch.return_value = "main"

    service = _make_service(mock_analyzer)
    result = service.analyze(str(tmp_path))

    assert result.monthly_commit_timeline[-1].month == "2018-05"
    assert sum(entry.commit_count for entry in result.monthly_commit_timeline) == result.total_commits == 2
