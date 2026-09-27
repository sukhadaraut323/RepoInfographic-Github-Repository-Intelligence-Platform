"""Unit tests for app.services.activity_analyzer.ActivityAnalyzer."""

from app.schemas.git_history import ActivityLevel
from app.services.activity_analyzer import ActivityAnalyzer
from app.tests.factories import make_git_history_result

ANALYZER = ActivityAnalyzer()


def test_high_activity_established_repo_scores_100() -> None:
    result = make_git_history_result(
        recent_activity_level=ActivityLevel.HIGH,
        average_commits_per_month=25.0,
        unique_contributors=15,
        repository_age_days=1000,
    )

    score = ANALYZER.analyze(result)

    assert score.score == 100.0
    assert score.reasons == []


def test_dormant_new_repo_scores_low() -> None:
    result = make_git_history_result(
        recent_activity_level=ActivityLevel.DORMANT,
        average_commits_per_month=0.0,
        unique_contributors=1,
        repository_age_days=5,
    )

    score = ANALYZER.analyze(result)

    assert score.score < 20.0
    assert len(score.reasons) > 0


def test_medium_activity_partial_credit() -> None:
    result = make_git_history_result(
        recent_activity_level=ActivityLevel.MEDIUM,
        average_commits_per_month=10.0,
        unique_contributors=5,
        repository_age_days=500,
    )

    score = ANALYZER.analyze(result)

    assert 0 < score.score < 100
    assert any("Medium" in e for e in score.evidence)


def test_score_never_exceeds_100() -> None:
    result = make_git_history_result(
        recent_activity_level=ActivityLevel.HIGH,
        average_commits_per_month=1000.0,
        unique_contributors=1000,
        repository_age_days=100000,
    )

    score = ANALYZER.analyze(result)

    assert score.score <= 100.0
