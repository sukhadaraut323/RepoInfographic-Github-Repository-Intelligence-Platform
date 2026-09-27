"""
LanguageDetector — Module 3 component.

Responsible for two purely lookup-based tasks:
    1. Mapping a file extension to a human-readable language name.
    2. Detecting project type(s) from well-known marker filenames
       (requirements.txt, package.json, pom.xml, pyproject.toml, etc.)

Also exposes the comment-syntax table used by `FileAnalyzer` to count
comment lines. This is a simple, line-based heuristic (matching known
line-comment prefixes and block-comment delimiters) — not a language
parser, and it deliberately does not attempt to resolve nested strings,
escaped delimiters, or other parser-level complexity. That precision is
out of scope for Module 3.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- Extension → language name -------------------------------------------------
EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".pyw": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript (JSX)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (TSX)",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".h": "C Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rs": "Rust",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".ps1": "PowerShell",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".sql": "SQL",
    ".r": "R",
    ".pl": "Perl",
    ".lua": "Lua",
    ".dart": "Dart",
    ".vue": "Vue",
    ".toml": "TOML",
    ".dockerfile": "Dockerfile",
    ".proto": "Protocol Buffers",
    ".graphql": "GraphQL",
}

# --- Project marker filename → project type label -------------------------------
PROJECT_MARKER_FILES: Dict[str, str] = {
    "requirements.txt": "Python (pip)",
    "pyproject.toml": "Python (pyproject)",
    "setup.py": "Python (setuptools)",
    "pipfile": "Python (Pipenv)",
    "package.json": "Node.js",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "build.gradle.kts": "Java/Kotlin (Gradle)",
    "cargo.toml": "Rust (Cargo)",
    "go.mod": "Go (Modules)",
    "gemfile": "Ruby (Bundler)",
    "composer.json": "PHP (Composer)",
    "mix.exs": "Elixir (Mix)",
    "dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
}


@dataclass(frozen=True)
class CommentSyntax:
    """Comment tokens used for approximate, line-based comment counting."""

    line_prefixes: List[str] = field(default_factory=list)
    block_delimiters: List[Tuple[str, str]] = field(default_factory=list)


_DEFAULT_COMMENT_SYNTAX = CommentSyntax()

_C_STYLE = CommentSyntax(line_prefixes=["//"], block_delimiters=[("/*", "*/")])

COMMENT_SYNTAX_MAP: Dict[str, CommentSyntax] = {
    "Python": CommentSyntax(line_prefixes=["#"], block_delimiters=[('"""', '"""'), ("'''", "'''")]),
    "JavaScript": _C_STYLE,
    "JavaScript (JSX)": _C_STYLE,
    "TypeScript": _C_STYLE,
    "TypeScript (TSX)": _C_STYLE,
    "Java": _C_STYLE,
    "Kotlin": _C_STYLE,
    "Go": _C_STYLE,
    "C": _C_STYLE,
    "C Header": _C_STYLE,
    "C++": _C_STYLE,
    "C++ Header": _C_STYLE,
    "C#": _C_STYLE,
    "Rust": _C_STYLE,
    "Swift": _C_STYLE,
    "Scala": _C_STYLE,
    "Dart": _C_STYLE,
    "PHP": CommentSyntax(line_prefixes=["//", "#"], block_delimiters=[("/*", "*/")]),
    "SCSS": _C_STYLE,
    "Less": _C_STYLE,
    "CSS": CommentSyntax(block_delimiters=[("/*", "*/")]),
    "Ruby": CommentSyntax(line_prefixes=["#"], block_delimiters=[("=begin", "=end")]),
    "Shell": CommentSyntax(line_prefixes=["#"]),
    "PowerShell": CommentSyntax(line_prefixes=["#"], block_delimiters=[("<#", "#>")]),
    "R": CommentSyntax(line_prefixes=["#"]),
    "Perl": CommentSyntax(line_prefixes=["#"]),
    "Lua": CommentSyntax(line_prefixes=["--"], block_delimiters=[("--[[", "]]")]),
    "SQL": CommentSyntax(line_prefixes=["--"], block_delimiters=[("/*", "*/")]),
    "HTML": CommentSyntax(block_delimiters=[("<!--", "-->")]),
    "XML": CommentSyntax(block_delimiters=[("<!--", "-->")]),
    "Vue": CommentSyntax(block_delimiters=[("<!--", "-->")]),
    "Objective-C": _C_STYLE,
    "Dockerfile": CommentSyntax(line_prefixes=["#"]),
    "GraphQL": CommentSyntax(line_prefixes=["#"]),
}


class LanguageDetector:
    """Detects a file's language from its extension and a repo's project type(s)."""

    @staticmethod
    def detect_language(file_path: Path) -> Optional[str]:
        """
        Return the language name for `file_path`, or None if unrecognized.

        Files without an extension (e.g. "Dockerfile", "Makefile") are
        matched by exact lowercase filename as a fallback.
        """
        suffix = file_path.suffix.lower()
        if suffix in EXTENSION_LANGUAGE_MAP:
            return EXTENSION_LANGUAGE_MAP[suffix]

        name_lower = file_path.name.lower()
        if name_lower == "dockerfile":
            return "Dockerfile"
        if name_lower == "makefile":
            return "Makefile"
        return None

    @staticmethod
    def get_comment_syntax(language: Optional[str]) -> CommentSyntax:
        """Return the comment syntax table for `language`, or an empty one."""
        if language is None:
            return _DEFAULT_COMMENT_SYNTAX
        return COMMENT_SYNTAX_MAP.get(language, _DEFAULT_COMMENT_SYNTAX)

    @staticmethod
    def detect_project_types(file_names: List[str]) -> List[str]:
        """
        Detect project type(s) present in the repository from marker filenames.

        Args:
            file_names: Filenames found anywhere in the scanned repository
                (basenames only, as returned by RepositoryScanner).

        Returns:
            A de-duplicated, order-preserved list of detected project type labels.
        """
        lower_names = {name.lower() for name in file_names}
        detected: List[str] = []
        for marker, label in PROJECT_MARKER_FILES.items():
            if marker in lower_names and label not in detected:
                detected.append(label)
        return detected
