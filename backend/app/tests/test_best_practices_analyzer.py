"""Unit tests for app.services.best_practices_analyzer.BestPracticesAnalyzer."""

from app.services.best_practices_analyzer import BestPracticesAnalyzer
from app.tests.factories import make_marker_files, make_static_analysis_result

ANALYZER = BestPracticesAnalyzer()


def test_full_best_practices_scores_100() -> None:
    markers = make_marker_files(
        dockerfile="Dockerfile",
        docker_compose="docker-compose.yml",
        gitignore=".gitignore",
        editorconfig=".editorconfig",
        env_example=".env.example",
        precommit_config=".pre-commit-config.yaml",
        has_ci_config=True,
    )
    result = make_static_analysis_result(marker_files=markers)

    score = ANALYZER.analyze(result)

    assert score.score == 100.0
    assert score.reasons == []


def test_nothing_present_scores_zero() -> None:
    result = make_static_analysis_result(marker_files=make_marker_files())

    score = ANALYZER.analyze(result)

    assert score.score == 0.0
    assert len(score.reasons) == 7


def test_gitignore_only_scores_15() -> None:
    result = make_static_analysis_result(marker_files=make_marker_files(gitignore=".gitignore"))

    score = ANALYZER.analyze(result)

    assert score.score == 15.0


def test_ci_config_detected_scores_25() -> None:
    result = make_static_analysis_result(marker_files=make_marker_files(has_ci_config=True))

    score = ANALYZER.analyze(result)

    assert score.score == 25.0
    assert any("CI configuration detected" in e for e in score.evidence)
