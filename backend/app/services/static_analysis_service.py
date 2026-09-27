"""
Service layer for Module 3 — Static Code Analysis.

Orchestrates:
    1. `RepositoryScanner` — filesystem traversal (files, directories, tree).
    2. `LanguageDetector`  — per-file language lookup + project type detection.
    3. `FileAnalyzer`      — per-file total/blank/comment line counting.

No repository code is ever executed. No complexity, dependency-graph,
security, or AI-derived data is computed here — this module reports only
directly observable, countable facts about the repository's files.
"""

import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.schemas.static_analysis import LanguageDistributionEntry, StaticAnalysisResult
from app.services.file_analyzer import FileAnalyzer
from app.services.language_detector import LanguageDetector
from app.services.repository_scanner import RepositoryScanner

logger = logging.getLogger(__name__)


class StaticAnalysisService:
    """Performs non-executing static analysis of a previously cloned repository."""

    def __init__(
        self,
        scanner: RepositoryScanner,
        file_analyzer: FileAnalyzer,
        language_detector: LanguageDetector,
        ignored_directories: List[str],
    ) -> None:
        self._scanner = scanner
        self._file_analyzer = file_analyzer
        self._language_detector = language_detector
        self._ignored_directories = ignored_directories

    def analyze(self, local_path: str) -> StaticAnalysisResult:
        """
        Scan and analyze the repository at `local_path`.

        Args:
            local_path: Path to a repository previously cloned by Module 2.

        Returns:
            A populated `StaticAnalysisResult`.

        Raises:
            RepositoryPathNotFoundError: If `local_path` does not exist or
                is not a directory.
        """
        root = Path(local_path)
        logger.info("Starting static analysis for %s", root)

        scan_result = self._scanner.scan(root)

        language_file_counts: Counter = Counter()
        total_lines = 0
        blank_lines = 0
        comment_lines = 0
        supported_source_files = 0

        for file_path in scan_result.files:
            language = self._language_detector.detect_language(file_path)
            if language is None:
                continue

            supported_source_files += 1
            language_file_counts[language] += 1

            comment_syntax = self._language_detector.get_comment_syntax(language)
            file_stats = self._file_analyzer.analyze_file(file_path, comment_syntax)

            total_lines += file_stats.total_lines
            blank_lines += file_stats.blank_lines
            comment_lines += file_stats.comment_lines

        language_distribution = self._build_language_distribution(
            language_file_counts, supported_source_files
        )

        project_types = self._language_detector.detect_project_types(
            [file_path.name for file_path in scan_result.files]
        )

        result = StaticAnalysisResult(
            local_path=str(root),
            total_files=len(scan_result.files),
            total_directories=len(scan_result.directories),
            supported_source_files=supported_source_files,
            language_distribution=language_distribution,
            total_lines=total_lines,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            project_types=project_types,
            directory_tree=scan_result.directory_tree,
            ignored_directories=sorted(self._ignored_directories),
            scanned_at=datetime.now(timezone.utc),
        )

        logger.info(
            "Completed static analysis for %s: %d files, %d supported, %d lines",
            root,
            result.total_files,
            result.supported_source_files,
            result.total_lines,
        )
        return result

    @staticmethod
    def _build_language_distribution(
        language_file_counts: Counter, supported_source_files: int
    ) -> List[LanguageDistributionEntry]:
        """Build a percentage-annotated, descending-order language breakdown."""
        if supported_source_files == 0:
            return []

        entries = [
            LanguageDistributionEntry(
                language=language,
                file_count=count,
                percentage=round((count / supported_source_files) * 100, 2),
            )
            for language, count in language_file_counts.items()
        ]
        entries.sort(key=lambda entry: entry.file_count, reverse=True)
        return entries
