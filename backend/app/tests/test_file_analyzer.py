"""Unit tests for app.services.file_analyzer.FileAnalyzer."""

from pathlib import Path

from app.services.file_analyzer import FileAnalyzer
from app.services.language_detector import LanguageDetector

ANALYZER = FileAnalyzer(max_file_size_bytes=2_000_000)


def test_analyze_file_counts_python_lines(tmp_path: Path) -> None:
    content = (
        "# module docstring\n"
        "import os\n"
        "\n"
        "def foo():\n"
        "    # a comment\n"
        "    return os.getcwd()\n"
        "\n"
    )
    file_path = tmp_path / "sample.py"
    file_path.write_text(content)

    syntax = LanguageDetector.get_comment_syntax("Python")
    stats = ANALYZER.analyze_file(file_path, syntax)

    assert stats.total_lines == 7
    assert stats.blank_lines == 2
    assert stats.comment_lines == 2


def test_analyze_file_counts_block_comments(tmp_path: Path) -> None:
    content = (
        "/* file header\n"
        " * more header\n"
        " */\n"
        "int main() {\n"
        "    return 0;\n"
        "}\n"
    )
    file_path = tmp_path / "sample.c"
    file_path.write_text(content)

    syntax = LanguageDetector.get_comment_syntax("C")
    stats = ANALYZER.analyze_file(file_path, syntax)

    assert stats.total_lines == 6
    assert stats.comment_lines == 3
    assert stats.blank_lines == 0


def test_analyze_file_handles_empty_file(tmp_path: Path) -> None:
    file_path = tmp_path / "empty.py"
    file_path.write_text("")

    syntax = LanguageDetector.get_comment_syntax("Python")
    stats = ANALYZER.analyze_file(file_path, syntax)

    assert stats.total_lines == 0
    assert stats.blank_lines == 0
    assert stats.comment_lines == 0


def test_analyze_file_skips_binary_file(tmp_path: Path) -> None:
    file_path = tmp_path / "binary.py"
    file_path.write_bytes(b"\x00\x01\x02PYC binary content")

    syntax = LanguageDetector.get_comment_syntax("Python")
    stats = ANALYZER.analyze_file(file_path, syntax)

    assert stats.total_lines == 0
    assert stats.blank_lines == 0
    assert stats.comment_lines == 0


def test_analyze_file_skips_oversized_file(tmp_path: Path) -> None:
    small_analyzer = FileAnalyzer(max_file_size_bytes=10)
    file_path = tmp_path / "big.py"
    file_path.write_text("x = 1\n" * 5)  # well over 10 bytes

    syntax = LanguageDetector.get_comment_syntax("Python")
    stats = small_analyzer.analyze_file(file_path, syntax)

    assert stats.total_lines == 0


def test_analyze_file_missing_file_returns_zero_stats(tmp_path: Path) -> None:
    file_path = tmp_path / "does_not_exist.py"
    syntax = LanguageDetector.get_comment_syntax("Python")

    stats = ANALYZER.analyze_file(file_path, syntax)

    assert stats.total_lines == 0
    assert stats.blank_lines == 0
    assert stats.comment_lines == 0
