"""Unit tests for app.services.codebase_analyzer.CodebaseAnalyzer."""

from app.schemas.static_analysis import LanguageDistributionEntry
from app.services.codebase_analyzer import CodebaseAnalyzer
from app.tests.factories import dir_node, file_node, make_directory_tree, make_static_analysis_result

ANALYZER = CodebaseAnalyzer()


# --- Codebase Score ---


def test_codebase_full_marks() -> None:
    tree = make_directory_tree(children=[dir_node("src", children=[file_node("main.py")])])
    result = make_static_analysis_result(
        directory_tree=tree,
        total_directories=1,
        supported_source_files=5,
        project_types=["Python (pip)"],
        language_distribution=[LanguageDistributionEntry(language="Python", file_count=5, percentage=100.0)],
    )

    score = ANALYZER.analyze_codebase(result)

    assert score.score == 100.0


def test_codebase_no_project_type_loses_25() -> None:
    result = make_static_analysis_result(project_types=[], total_directories=1, supported_source_files=5)

    score = ANALYZER.analyze_codebase(result)

    assert score.score == 75.0


def test_codebase_flat_structure_loses_25() -> None:
    result = make_static_analysis_result(
        project_types=["Python (pip)"], total_directories=0, supported_source_files=5
    )

    score = ANALYZER.analyze_codebase(result)

    assert score.score == 75.0


def test_codebase_fragmented_language_loses_25() -> None:
    result = make_static_analysis_result(
        project_types=["Python (pip)"],
        total_directories=1,
        supported_source_files=5,
        language_distribution=[
            LanguageDistributionEntry(language="Python", file_count=2, percentage=30.0),
            LanguageDistributionEntry(language="JavaScript", file_count=2, percentage=30.0),
            LanguageDistributionEntry(language="Go", file_count=1, percentage=40.0),
        ],
    )

    # Top language is 40% which meets threshold exactly (>= 40).
    score = ANALYZER.analyze_codebase(result)
    assert score.score == 100.0

    # Now push it below the threshold.
    result_low = make_static_analysis_result(
        project_types=["Python (pip)"],
        total_directories=1,
        supported_source_files=5,
        language_distribution=[
            LanguageDistributionEntry(language="Python", file_count=2, percentage=39.0),
            LanguageDistributionEntry(language="JavaScript", file_count=2, percentage=39.0),
            LanguageDistributionEntry(language="Go", file_count=1, percentage=22.0),
        ],
    )
    score_low = ANALYZER.analyze_codebase(result_low)
    assert score_low.score == 75.0


def test_codebase_no_source_content_loses_25() -> None:
    result = make_static_analysis_result(
        project_types=["Python (pip)"], total_directories=1, supported_source_files=1
    )

    score = ANALYZER.analyze_codebase(result)

    assert score.score == 75.0


# --- Maintainability Score ---


def test_maintainability_healthy_file_size_and_structure() -> None:
    tree = make_directory_tree(children=[dir_node("src", children=[dir_node("app", children=[file_node("a.py")])])])
    result = make_static_analysis_result(
        directory_tree=tree,
        total_files=10,
        total_directories=2,
        supported_source_files=10,
        total_lines=1000,  # 100 lines/file average -> healthy
    )

    score = ANALYZER.analyze_maintainability(result)

    assert score.score == 100.0


def test_maintainability_no_source_files_scores_low() -> None:
    result = make_static_analysis_result(supported_source_files=0, total_lines=0, total_files=0, total_directories=0)

    score = ANALYZER.analyze_maintainability(result)

    assert score.score < 40.0


def test_maintainability_very_large_files_penalized() -> None:
    tree = make_directory_tree(children=[dir_node("src", children=[dir_node("app")])])
    result = make_static_analysis_result(
        directory_tree=tree, supported_source_files=2, total_lines=2000, total_files=2, total_directories=2
    )

    score = ANALYZER.analyze_maintainability(result)

    assert any("large" in reason.lower() for reason in score.reasons)


def test_maintainability_flat_repo_penalized_for_depth() -> None:
    tree = make_directory_tree(children=[file_node("a.py"), file_node("b.py")])
    result = make_static_analysis_result(
        directory_tree=tree, total_files=2, total_directories=0, supported_source_files=2, total_lines=200
    )

    score = ANALYZER.analyze_maintainability(result)

    assert any("directory structure" in reason.lower() or "nesting" in reason.lower() for reason in score.reasons)
