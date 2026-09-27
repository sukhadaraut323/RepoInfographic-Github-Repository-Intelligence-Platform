"""Unit tests for app.services.largest_directories_formatter.LargestDirectoriesFormatter."""

from app.services.largest_directories_formatter import LargestDirectoriesFormatter
from app.tests.factories import dir_node, file_node, make_directory_tree, make_static_analysis_result

FORMATTER = LargestDirectoriesFormatter(limit=10)


def test_counts_files_recursively_per_top_level_directory() -> None:
    tree = make_directory_tree(
        children=[
            dir_node(
                "src",
                children=[
                    file_node("a.py"),
                    file_node("b.py"),
                    dir_node("nested", children=[file_node("c.py")]),
                ],
            ),
            dir_node("tests", children=[file_node("test_a.py")]),
            file_node("README.md"),  # top-level file, should not appear as a directory
        ]
    )
    result = make_static_analysis_result(directory_tree=tree)

    entries = FORMATTER.format(result)

    entries_by_name = {e.name: e.file_count for e in entries}
    assert entries_by_name["src"] == 3
    assert entries_by_name["tests"] == 1
    assert "README.md" not in entries_by_name


def test_sorted_descending_by_file_count() -> None:
    tree = make_directory_tree(
        children=[
            dir_node("small", children=[file_node("a.py")]),
            dir_node("big", children=[file_node("a.py"), file_node("b.py"), file_node("c.py")]),
        ]
    )
    result = make_static_analysis_result(directory_tree=tree)

    entries = FORMATTER.format(result)

    assert entries[0].name == "big"
    assert entries[1].name == "small"


def test_respects_limit() -> None:
    tree = make_directory_tree(
        children=[dir_node(f"dir_{i}", children=[file_node("a.py")]) for i in range(5)]
    )
    result = make_static_analysis_result(directory_tree=tree)
    limited_formatter = LargestDirectoriesFormatter(limit=2)

    entries = limited_formatter.format(result)

    assert len(entries) == 2


def test_no_directories_returns_empty_list() -> None:
    tree = make_directory_tree(children=[file_node("README.md")])
    result = make_static_analysis_result(directory_tree=tree)

    entries = FORMATTER.format(result)

    assert entries == []
