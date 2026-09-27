"""Unit tests for app.services.documentation_analyzer.DocumentationAnalyzer."""

from app.services.documentation_analyzer import DocumentationAnalyzer
from app.tests.factories import dir_node, file_node, make_directory_tree, make_static_analysis_result

ANALYZER = DocumentationAnalyzer()


def test_full_documentation_scores_100() -> None:
    tree = make_directory_tree(
        children=[
            file_node("README.md"),
            file_node("LICENSE"),
            file_node("CONTRIBUTING.md"),
            file_node("CHANGELOG.md"),
            dir_node("docs", children=[file_node("mkdocs.yml")]),
        ]
    )
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 100.0
    assert score.reasons == []


def test_missing_everything_scores_zero() -> None:
    tree = make_directory_tree(children=[file_node("index.py")])
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 0.0
    assert len(score.reasons) == 6  # README, LICENSE, CONTRIBUTING, CHANGELOG, docs, API docs


def test_readme_only_scores_30() -> None:
    tree = make_directory_tree(children=[file_node("README.md")])
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 30.0
    assert any("README" in e for e in score.evidence)


def test_case_insensitive_readme_detection() -> None:
    tree = make_directory_tree(children=[file_node("readme.md")])
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 30.0


def test_docs_folder_alone_scores_10() -> None:
    tree = make_directory_tree(children=[dir_node("docs")])
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 10.0
