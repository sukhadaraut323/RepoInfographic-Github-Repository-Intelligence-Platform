"""
Integration tests for AnalyticsService.

Exercises the full pipeline (all eight real formatters) end-to-end — no
mocking, since Module 6 performs pure computation with no external I/O.
"""

import pytest

from app.services.analytics_service import AnalyticsService
from app.services.commit_timeline_formatter import CommitTimelineFormatter
from app.services.file_type_distribution_formatter import FileTypeDistributionFormatter
from app.services.health_gauge_formatter import HealthGaugeFormatter
from app.services.language_distribution_formatter import LanguageDistributionFormatter
from app.services.largest_directories_formatter import LargestDirectoriesFormatter
from app.services.overview_cards_formatter import OverviewCardsFormatter
from app.services.repository_timeline_formatter import RepositoryTimelineFormatter
from app.services.score_breakdown_formatter import ScoreBreakdownFormatter
from app.tests.analytics_factories import make_repository_metrics_result
from app.tests.factories import (
    dir_node,
    file_node,
    make_directory_tree,
    make_git_history_result,
    make_repository_metadata,
    make_static_analysis_result,
)


@pytest.fixture
def service() -> AnalyticsService:
    return AnalyticsService(
        language_distribution_formatter=LanguageDistributionFormatter(),
        commit_timeline_formatter=CommitTimelineFormatter(),
        overview_cards_formatter=OverviewCardsFormatter(),
        health_gauge_formatter=HealthGaugeFormatter(
            excellent_threshold=85.0, good_threshold=70.0, fair_threshold=50.0
        ),
        score_breakdown_formatter=ScoreBreakdownFormatter(),
        repository_timeline_formatter=RepositoryTimelineFormatter(),
        file_type_distribution_formatter=FileTypeDistributionFormatter(),
        largest_directories_formatter=LargestDirectoriesFormatter(limit=10),
    )


def test_build_dashboard_returns_all_eight_sections(service) -> None:
    tree = make_directory_tree(children=[dir_node("src", children=[file_node("main.py")])])
    metadata = make_repository_metadata(stargazers_count=500)
    static_result = make_static_analysis_result(directory_tree=tree, total_files=3, supported_source_files=2)
    history_result = make_git_history_result(unique_contributors=5)
    metrics_result = make_repository_metrics_result(overall_health_score=77.0)

    dashboard = service.build_dashboard(metadata, static_result, history_result, metrics_result)

    assert isinstance(dashboard.language_distribution, list)
    assert isinstance(dashboard.commit_timeline, list)
    assert len(dashboard.overview_cards) == 9
    assert dashboard.health_gauge.value == 77.0
    assert dashboard.health_gauge.status == "Good"
    assert len(dashboard.score_breakdown) == 6
    assert len(dashboard.repository_timeline) >= 1
    assert isinstance(dashboard.file_type_distribution, list)
    assert len(dashboard.largest_directories) == 1
    assert dashboard.largest_directories[0].name == "src"
    assert dashboard.generated_at is not None


def test_dashboard_is_json_serializable(service) -> None:
    metadata = make_repository_metadata()
    static_result = make_static_analysis_result()
    history_result = make_git_history_result()
    metrics_result = make_repository_metrics_result()

    dashboard = service.build_dashboard(metadata, static_result, history_result, metrics_result)

    payload = dashboard.model_dump(mode="json")
    assert "language_distribution" in payload
    assert "largest_directories" in payload
