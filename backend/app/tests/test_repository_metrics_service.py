"""
Integration tests for RepositoryMetricsService.

Exercises the full pipeline (all five real analyzers + the real
HealthScoreCalculator) end-to-end — no mocking, since Module 5 performs
pure computation with no external I/O.
"""

import pytest

from app.services.activity_analyzer import ActivityAnalyzer
from app.services.best_practices_analyzer import BestPracticesAnalyzer
from app.services.codebase_analyzer import CodebaseAnalyzer
from app.services.community_analyzer import CommunityAnalyzer
from app.services.documentation_analyzer import DocumentationAnalyzer
from app.services.health_score_calculator import HealthScoreCalculator
from app.services.repository_metrics_service import RepositoryMetricsService
from app.tests.factories import (
    dir_node,
    file_node,
    make_directory_tree,
    make_git_history_result,
    make_repository_metadata,
    make_static_analysis_result,
)


@pytest.fixture
def service() -> RepositoryMetricsService:
    return RepositoryMetricsService(
        documentation_analyzer=DocumentationAnalyzer(),
        codebase_analyzer=CodebaseAnalyzer(),
        activity_analyzer=ActivityAnalyzer(),
        community_analyzer=CommunityAnalyzer(),
        best_practices_analyzer=BestPracticesAnalyzer(),
        health_score_calculator=HealthScoreCalculator(
            weight_documentation=0.15,
            weight_codebase=0.20,
            weight_activity=0.20,
            weight_community=0.15,
            weight_maintainability=0.15,
            weight_best_practices=0.15,
        ),
    )


def test_compute_metrics_well_maintained_repository(service) -> None:
    tree = make_directory_tree(
        children=[
            file_node("README.md"),
            file_node("LICENSE"),
            file_node(".gitignore"),
            dir_node(".github", children=[dir_node("workflows", children=[file_node("ci.yml")])]),
            dir_node("src", children=[file_node("main.py"), file_node("utils.py")]),
        ]
    )
    metadata = make_repository_metadata(
        full_name="octo/well-maintained", stargazers_count=2000, forks_count=200, watchers_count=500, open_issues_count=10
    )
    static_result = make_static_analysis_result(
        directory_tree=tree,
        total_files=5,
        total_directories=3,
        supported_source_files=2,
        total_lines=200,
        project_types=["Python (pip)"],
    )
    history_result = make_git_history_result(unique_contributors=20, repository_age_days=800)

    result = service.compute_metrics(metadata, static_result, history_result)

    assert 0 <= result.documentation_score.score <= 100
    assert 0 <= result.codebase_score.score <= 100
    assert 0 <= result.activity_score.score <= 100
    assert 0 <= result.community_score.score <= 100
    assert 0 <= result.maintainability_score.score <= 100
    assert 0 <= result.best_practices_score.score <= 100
    assert 0 <= result.overall_health_score.score <= 100

    # This repo has strong documentation and community signals, so it should
    # score reasonably well overall.
    assert result.overall_health_score.score > 50
    assert result.calculated_at is not None


def test_compute_metrics_empty_repository_scores_low(service) -> None:
    metadata = make_repository_metadata(
        full_name="octo/empty", stargazers_count=0, forks_count=0, watchers_count=0, open_issues_count=0
    )
    static_result = make_static_analysis_result(
        directory_tree=make_directory_tree(children=[]),
        total_files=0,
        total_directories=0,
        supported_source_files=0,
        total_lines=0,
        project_types=[],
    )
    history_result = make_git_history_result(
        unique_contributors=0,
        repository_age_days=0,
        total_commits=0,
        average_commits_per_month=0.0,
    )

    result = service.compute_metrics(metadata, static_result, history_result)

    assert result.overall_health_score.score < 40
    assert len(result.documentation_score.reasons) > 0
    assert len(result.best_practices_score.reasons) > 0


def test_result_contains_no_ai_generated_recommendation_fields(service) -> None:
    """Sanity check: the schema should only expose score/evidence/reasons, nothing else."""
    metadata = make_repository_metadata()
    static_result = make_static_analysis_result()
    history_result = make_git_history_result()

    result = service.compute_metrics(metadata, static_result, history_result)

    for sub_score in [
        result.documentation_score,
        result.codebase_score,
        result.activity_score,
        result.community_score,
        result.maintainability_score,
        result.best_practices_score,
        result.overall_health_score,
    ]:
        assert set(sub_score.model_dump().keys()) == {"score", "evidence", "reasons"}
