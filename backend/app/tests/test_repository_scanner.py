"""Unit tests for app.services.repository_scanner.RepositoryScanner."""

from pathlib import Path

import pytest

from app.core.exceptions import RepositoryPathNotFoundError
from app.services.repository_scanner import RepositoryScanner

DEFAULT_IGNORED = [
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "coverage",
]


def _build_sample_repo(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hi')\n")
    (root / "README.md").write_text("# demo\n")

    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / "node_modules" / "pkg" / "index.js").write_text("module.exports = {};\n")

    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]\n")


@pytest.fixture
def scanner() -> RepositoryScanner:
    return RepositoryScanner(
        ignored_directories=DEFAULT_IGNORED, tree_max_depth=3, tree_max_entries_per_level=50
    )


def test_scan_raises_for_missing_path(scanner, tmp_path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(RepositoryPathNotFoundError):
        scanner.scan(missing)


def test_scan_raises_when_path_is_a_file(scanner, tmp_path) -> None:
    file_path = tmp_path / "not_a_directory.txt"
    file_path.write_text("hello")
    with pytest.raises(RepositoryPathNotFoundError):
        scanner.scan(file_path)


def test_scan_excludes_ignored_directories(scanner, tmp_path) -> None:
    _build_sample_repo(tmp_path)

    result = scanner.scan(tmp_path)
    file_names = {f.name for f in result.files}

    assert "main.py" in file_names
    assert "README.md" in file_names
    assert "index.js" not in file_names  # inside node_modules, ignored
    assert "config" not in file_names  # inside .git, ignored


def test_scan_counts_files_and_directories(scanner, tmp_path) -> None:
    _build_sample_repo(tmp_path)

    result = scanner.scan(tmp_path)

    # Only "src" should be counted as a directory (node_modules and .git are ignored).
    assert len(result.directories) == 1
    assert result.directories[0].name == "src"
    assert len(result.files) == 2  # main.py + README.md


def test_directory_tree_excludes_ignored_dirs(scanner, tmp_path) -> None:
    _build_sample_repo(tmp_path)

    result = scanner.scan(tmp_path)
    child_names = {child.name for child in result.directory_tree.children}

    assert "src" in child_names
    assert "README.md" in child_names
    assert "node_modules" not in child_names
    assert ".git" not in child_names


def test_directory_tree_respects_max_depth(tmp_path) -> None:
    nested = tmp_path / "a" / "b" / "c" / "d"
    nested.mkdir(parents=True)
    (nested / "deep.py").write_text("x = 1\n")

    shallow_scanner = RepositoryScanner(
        ignored_directories=[], tree_max_depth=2, tree_max_entries_per_level=50
    )
    result = shallow_scanner.scan(tmp_path)

    # depth 0 = root, depth 1 = "a", depth 2 = "b" -> "b" node should be truncated
    # with no children since it exceeds max_depth.
    node_a = result.directory_tree.children[0]
    node_b = node_a.children[0]
    assert node_b.children is None
    assert node_b.truncated is True


def test_directory_tree_respects_max_entries_per_level(tmp_path) -> None:
    for i in range(10):
        (tmp_path / f"file_{i}.py").write_text("x = 1\n")

    limited_scanner = RepositoryScanner(
        ignored_directories=[], tree_max_depth=3, tree_max_entries_per_level=3
    )
    result = limited_scanner.scan(tmp_path)

    assert len(result.directory_tree.children) == 3
    assert result.directory_tree.truncated is True
