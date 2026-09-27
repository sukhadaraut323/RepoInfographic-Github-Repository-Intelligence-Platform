"""Unit tests for app.services.best_practices_analyzer.BestPracticesAnalyzer."""

from app.services.best_practices_analyzer import BestPracticesAnalyzer
from app.tests.factories import dir_node, file_node, make_directory_tree, make_static_analysis_result

ANALYZER = BestPracticesAnalyzer()


def test_full_best_practices_scores_100() -> None:
    tree = make_directory_tree(
        children=[
            dir_node(".github", children=[dir_node("workflows", children=[file_node("ci.yml")])]),
            file_node("Dockerfile"),
            file_node("docker-compose.yml"),
            file_node(".gitignore"),
            file_node(".editorconfig"),
            file_node(".env.example"),
            file_node(".pre-commit-config.yaml"),
        ]
    )
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 100.0
    assert score.reasons == []


def test_nothing_present_scores_zero() -> None:
    tree = make_directory_tree(children=[file_node("main.py")])
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 0.0
    assert len(score.reasons) == 7


def test_gitignore_only_scores_15() -> None:
    tree = make_directory_tree(children=[file_node(".gitignore")])
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 15.0


def test_circleci_directory_counts_as_ci() -> None:
    tree = make_directory_tree(children=[dir_node(".circleci", children=[file_node("config.yml")])])
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 25.0
    assert any("CI configuration detected" in e for e in score.evidence)


def test_travis_file_counts_as_ci() -> None:
    tree = make_directory_tree(children=[file_node(".travis.yml")])
    result = make_static_analysis_result(directory_tree=tree)

    score = ANALYZER.analyze(result)

    assert score.score == 25.0
