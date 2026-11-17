"""Unit tests for app.services.score_breakdown_formatter.ScoreBreakdownFormatter."""

from app.services.score_breakdown_formatter import ScoreBreakdownFormatter
from app.tests.analytics_factories import make_repository_metrics_result

FORMATTER = ScoreBreakdownFormatter()


def test_returns_six_categories_with_correct_scores() -> None:
    result = make_repository_metrics_result(
        documentation_score=90,
        codebase_score=80,
        activity_score=70,
        community_score=60,
        maintainability_score=50,
        best_practices_score=40,
    )

    entries = FORMATTER.format(result)

    entries_by_category = {entry.category: entry.score for entry in entries}
    assert len(entries) == 6
    assert entries_by_category["Documentation"] == 90
    assert entries_by_category["Codebase"] == 80
    assert entries_by_category["Activity"] == 70
    assert entries_by_category["Community"] == 60
    assert entries_by_category["Maintainability"] == 50
    assert entries_by_category["Best Practices"] == 40


def test_does_not_include_overall_score() -> None:
    result = make_repository_metrics_result()

    entries = FORMATTER.format(result)

    categories = {entry.category for entry in entries}
    assert "Overall" not in categories
