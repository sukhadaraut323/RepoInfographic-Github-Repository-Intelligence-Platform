"""Unit tests for app.services.overview_cards_formatter.OverviewCardsFormatter."""

from app.services.overview_cards_formatter import OverviewCardsFormatter
from app.tests.analytics_factories import make_repository_metrics_result
from app.tests.factories import make_git_history_result, make_repository_metadata, make_static_analysis_result

FORMATTER = OverviewCardsFormatter()


def test_returns_expected_card_labels() -> None:
    metadata = make_repository_metadata(stargazers_count=100, forks_count=20, watchers_count=50, open_issues_count=5)
    static_result = make_static_analysis_result(total_files=42, total_lines=1000)
    history_result = make_git_history_result(unique_contributors=7, total_commits=300)
    metrics_result = make_repository_metrics_result(overall_health_score=82.5)

    cards = FORMATTER.format(metadata, static_result, history_result, metrics_result)

    cards_by_label = {card.label: card.value for card in cards}
    assert cards_by_label["Stars"] == 100
    assert cards_by_label["Forks"] == 20
    assert cards_by_label["Watchers"] == 50
    assert cards_by_label["Open Issues"] == 5
    assert cards_by_label["Contributors"] == 7
    assert cards_by_label["Total Commits"] == 300
    assert cards_by_label["Total Files"] == 42
    assert cards_by_label["Total Lines"] == 1000
    assert cards_by_label["Overall Health Score"] == 82.5


def test_returns_nine_cards() -> None:
    metadata = make_repository_metadata()
    static_result = make_static_analysis_result()
    history_result = make_git_history_result()
    metrics_result = make_repository_metrics_result()

    cards = FORMATTER.format(metadata, static_result, history_result, metrics_result)

    assert len(cards) == 9
