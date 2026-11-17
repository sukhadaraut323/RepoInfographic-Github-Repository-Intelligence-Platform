"""
Integration tests for StaticAnalysisService.

These build a small real directory tree on disk and run the full
scanner → language detector → file analyzer pipeline end-to-end, with
no mocking, since all of Module 3 operates purely on the local filesystem.
"""

from pathlib import Path

import pytest

from app.services.file_analyzer import FileAnalyzer
from app.services.language_detector import LanguageDetector
from app.services.marker_file_detector import MarkerFileDetector
from app.services.repository_scanner import RepositoryScanner
from app.services.static_analysis_service import StaticAnalysisService

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
    (root / "app").mkdir()
    (root / "app" / "main.py").write_text(
        "# entry point\n"
        "import sys\n"
        "\n"
        "def main():\n"
        "    return 0\n"
    )
    (root / "app" / "utils.js").write_text(
        "// helper functions\n"
        "function add(a, b) {\n"
        "    return a + b;\n"
        "}\n"
    )
    (root / "README.md").write_text("# Sample project\n")
    (root / "requirements.txt").write_text("fastapi\n")

    (root / "node_modules").mkdir()
    (root / "node_modules" / "ignored.js").write_text("// should not be counted\n")

    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"\x00\x01binary")


@pytest.fixture
def service() -> StaticAnalysisService:
    scanner = RepositoryScanner(
        ignored_directories=DEFAULT_IGNORED, tree_max_depth=3, tree_max_entries_per_level=50
    )
    file_analyzer = FileAnalyzer(max_file_size_bytes=2_000_000)
    return StaticAnalysisService(
        scanner=scanner,
        file_analyzer=file_analyzer,
        language_detector=LanguageDetector(),
        ignored_directories=DEFAULT_IGNORED,
        marker_file_detector=MarkerFileDetector(readme_max_chars=6000),
    )


def test_analyze_full_pipeline(service, tmp_path) -> None:
    _build_sample_repo(tmp_path)

    result = service.analyze(str(tmp_path))

    # Files: main.py, utils.js, README.md, requirements.txt = 4
    # (node_modules/ignored.js and __pycache__/*.pyc are excluded)
    assert result.total_files == 4
    assert result.total_directories == 1  # only "app"

    # Supported source files: main.py, utils.js, README.md, requirements.txt
    # (all 4 have recognized extensions: Python, JavaScript, Markdown, — but
    # requirements.txt has no recognized extension, so 3 supported source files)
    assert result.supported_source_files == 3

    languages = {entry.language: entry.file_count for entry in result.language_distribution}
    assert languages.get("Python") == 1
    assert languages.get("JavaScript") == 1
    assert languages.get("Markdown") == 1

    assert result.total_lines > 0
    assert result.comment_lines >= 2  # one comment in each of main.py and utils.js

    assert "Python (pip)" in result.project_types

    assert result.directory_tree.name == tmp_path.name
    child_names = {child.name for child in result.directory_tree.children}
    assert "node_modules" not in child_names
    assert "__pycache__" not in child_names

    assert result.ignored_directories == sorted(DEFAULT_IGNORED)
    assert result.local_path == str(tmp_path)

    # Real end-to-end marker-file detection and README content extraction,
    # from the real file scan (not the display tree).
    assert result.marker_files.readme.present is True
    assert result.marker_files.readme.path == "README.md"
    assert result.marker_files.license.present is False
    assert result.readme_content == "# Sample project\n"
    assert result.readme_truncated is False


def test_analyze_empty_repository(service, tmp_path) -> None:
    result = service.analyze(str(tmp_path))

    assert result.total_files == 0
    assert result.total_directories == 0
    assert result.supported_source_files == 0
    assert result.language_distribution == []
    assert result.total_lines == 0
    assert result.project_types == []
