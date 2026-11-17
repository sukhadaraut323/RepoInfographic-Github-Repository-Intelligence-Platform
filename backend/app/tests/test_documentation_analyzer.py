"""Unit tests for app.services.documentation_analyzer.DocumentationAnalyzer."""

from app.services.documentation_analyzer import DocumentationAnalyzer
from app.tests.factories import make_marker_files, make_static_analysis_result

ANALYZER = DocumentationAnalyzer()


def test_full_documentation_scores_100() -> None:
    markers = make_marker_files(
        readme="README.md", license="LICENSE", contributing="CONTRIBUTING.md", changelog="CHANGELOG.md",
        has_docs_directory=True, has_api_docs_tooling=True,
    )
    result = make_static_analysis_result(marker_files=markers)

    score = ANALYZER.analyze(result)

    assert score.score == 100.0
    assert score.reasons == []


def test_missing_everything_scores_zero() -> None:
    result = make_static_analysis_result(marker_files=make_marker_files())

    score = ANALYZER.analyze(result)

    assert score.score == 0.0
    assert len(score.reasons) == 6  # README, LICENSE, CONTRIBUTING, CHANGELOG, docs, API docs


def test_readme_only_scores_30() -> None:
    result = make_static_analysis_result(marker_files=make_marker_files(readme="README.md"))

    score = ANALYZER.analyze(result)

    assert score.score == 30.0
    assert any("README" in e for e in score.evidence)


def test_docs_folder_alone_scores_10() -> None:
    result = make_static_analysis_result(marker_files=make_marker_files(has_docs_directory=True))

    score = ANALYZER.analyze(result)

    assert score.score == 10.0
