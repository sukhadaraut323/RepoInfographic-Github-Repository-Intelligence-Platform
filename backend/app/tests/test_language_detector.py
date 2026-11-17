"""Unit tests for app.services.language_detector.LanguageDetector."""

from pathlib import Path

from app.services.language_detector import LanguageDetector


def test_detect_language_known_extensions() -> None:
    assert LanguageDetector.detect_language(Path("main.py")) == "Python"
    assert LanguageDetector.detect_language(Path("index.js")) == "JavaScript"
    assert LanguageDetector.detect_language(Path("App.tsx")) == "TypeScript (TSX)"
    assert LanguageDetector.detect_language(Path("Main.java")) == "Java"


def test_detect_language_unknown_extension_returns_none() -> None:
    assert LanguageDetector.detect_language(Path("binary.exe")) is None
    assert LanguageDetector.detect_language(Path("no_extension_file")) is None


def test_detect_language_special_filenames() -> None:
    assert LanguageDetector.detect_language(Path("Dockerfile")) == "Dockerfile"
    assert LanguageDetector.detect_language(Path("Makefile")) == "Makefile"


def test_get_comment_syntax_python() -> None:
    syntax = LanguageDetector.get_comment_syntax("Python")
    assert "#" in syntax.line_prefixes
    assert ('"""', '"""') in syntax.block_delimiters


def test_get_comment_syntax_unknown_language_returns_empty() -> None:
    syntax = LanguageDetector.get_comment_syntax("SomeUnknownLanguage")
    assert syntax.line_prefixes == []
    assert syntax.block_delimiters == []


def test_detect_project_types_python_pip() -> None:
    result = LanguageDetector.detect_project_types(["requirements.txt", "main.py"])
    assert "Python (pip)" in result


def test_detect_project_types_multiple_markers() -> None:
    result = LanguageDetector.detect_project_types(
        ["package.json", "pyproject.toml", "README.md"]
    )
    assert "Node.js" in result
    assert "Python (pyproject)" in result


def test_detect_project_types_no_markers_returns_empty() -> None:
    result = LanguageDetector.detect_project_types(["README.md", "LICENSE"])
    assert result == []


def test_detect_project_types_is_case_insensitive() -> None:
    result = LanguageDetector.detect_project_types(["REQUIREMENTS.TXT"])
    assert "Python (pip)" in result
