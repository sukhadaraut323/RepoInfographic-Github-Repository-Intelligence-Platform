"""
FileAnalyzer — Module 3 component.

Reads a single text file (without ever executing it) and counts total,
blank, and comment lines using the comment syntax supplied by
`LanguageDetector`. This is intentionally a simple, line-based counter —
not a parser or complexity analyzer.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from app.services.language_detector import CommentSyntax

logger = logging.getLogger(__name__)

_BINARY_PROBE_SIZE = 8192


@dataclass(frozen=True)
class FileLineStats:
    """Line counts for a single file."""

    total_lines: int
    blank_lines: int
    comment_lines: int


class FileAnalyzer:
    """Counts total/blank/comment lines for a single source file."""

    def __init__(self, max_file_size_bytes: int) -> None:
        self._max_file_size_bytes = max_file_size_bytes

    def analyze_file(self, file_path: Path, comment_syntax: CommentSyntax) -> FileLineStats:
        """
        Analyze a single file and return its line statistics.

        Files that are too large, unreadable, or appear to be binary are
        skipped and reported as zero-line statistics — they are still
        counted toward `total_files` and language distribution upstream,
        but do not contribute to line totals.
        """
        try:
            if file_path.stat().st_size > self._max_file_size_bytes:
                logger.debug("Skipping oversized file for line counting: %s", file_path)
                return FileLineStats(total_lines=0, blank_lines=0, comment_lines=0)

            if self._looks_binary(file_path):
                logger.debug("Skipping binary file for line counting: %s", file_path)
                return FileLineStats(total_lines=0, blank_lines=0, comment_lines=0)

            text = file_path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError) as exc:
            logger.debug("Skipping unreadable file %s: %s", file_path, exc)
            return FileLineStats(total_lines=0, blank_lines=0, comment_lines=0)

        return self._count_lines(text, comment_syntax)

    @staticmethod
    def _looks_binary(file_path: Path) -> bool:
        """Heuristic: a null byte in the first chunk indicates a binary file."""
        try:
            with file_path.open("rb") as handle:
                chunk = handle.read(_BINARY_PROBE_SIZE)
            return b"\x00" in chunk
        except OSError:
            return True

    @staticmethod
    def _count_lines(text: str, comment_syntax: CommentSyntax) -> FileLineStats:
        lines = text.splitlines()
        total = len(lines)
        blank = 0
        comment = 0

        in_block_comment = False
        active_block_end: str = ""

        for raw_line in lines:
            stripped = raw_line.strip()

            if not stripped:
                blank += 1
                continue

            if in_block_comment:
                comment += 1
                if active_block_end in stripped:
                    in_block_comment = False
                continue

            matched_block = False
            for start_token, end_token in comment_syntax.block_delimiters:
                if stripped.startswith(start_token):
                    comment += 1
                    remainder = stripped[len(start_token):]
                    if end_token not in remainder:
                        in_block_comment = True
                        active_block_end = end_token
                    matched_block = True
                    break
            if matched_block:
                continue

            if any(stripped.startswith(prefix) for prefix in comment_syntax.line_prefixes):
                comment += 1

        return FileLineStats(total_lines=total, blank_lines=blank, comment_lines=comment)
