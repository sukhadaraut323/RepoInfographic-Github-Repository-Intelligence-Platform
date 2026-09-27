"""Unit tests for app.services.community_analyzer.CommunityAnalyzer."""

from app.services.community_analyzer import CommunityAnalyzer
from app.tests.factories import make_git_history_result, make_repository_metadata

ANALYZER = CommunityAnalyzer()


def test_popular_repository_scores_high() -> None:
    metadata = make_repository_metadata(
        stargazers_count=5000, forks_count=500, watchers_count=1000, open_issues_count=20
    )
    history = make_git_history_result(unique_contributors=50)

    score = ANALYZER.analyze(metadata, history)

    assert score.score == 100.0
    assert score.reasons == []


def test_no_engagement_scores_zero() -> None:
    metadata = make_repository_metadata(
        stargazers_count=0, forks_count=0, watchers_count=0, open_issues_count=0
    )
    history = make_git_history_result(unique_contributors=0)

    score = ANALYZER.analyze(metadata, history)

    assert score.score == 0.0
    assert len(score.reasons) == 5


def test_moderate_engagement_partial_score() -> None:
    metadata = make_repository_metadata(
        stargazers_count=50, forks_count=5, watchers_count=20, open_issues_count=3
    )
    history = make_git_history_result(unique_contributors=2)

    score = ANALYZER.analyze(metadata, history)

    assert 0 < score.score < 100


def test_open_issues_presence_contributes_engagement_points() -> None:
    metadata_with_issues = make_repository_metadata(open_issues_count=5)
    metadata_without_issues = make_repository_metadata(open_issues_count=0)
    history = make_git_history_result(unique_contributors=0)

    score_with = ANALYZER.analyze(metadata_with_issues, history)
    score_without = ANALYZER.analyze(metadata_without_issues, history)

    assert score_with.score > score_without.score
