"""
CodebaseAnalyzer — Module 5 component.

Computes two related but distinct scores, both derived entirely from
Module 3's `StaticAnalysisResult` (no re-scanning of the filesystem):

    - Codebase Score: directory organization, project structure,
      configuration/project-type detection, language cohesion.
    - Maintainability Score: average file size (in lines — Module 3 does
      not expose byte sizes), directory depth, and files-per-directory
      organization.

These are kept as two methods on one analyzer, rather than two separate
classes, because both draw on exactly the same upstream data source and
the same directory-tree traversal helpers.
"""

import logging
from typing import List

from app.schemas.metrics import SubScore
from app.schemas.static_analysis import StaticAnalysisResult
from app.utils.directory_tree_utils import max_tree_depth

logger = logging.getLogger(__name__)

# --- Codebase Score weights (sum to 100) ---
_PROJECT_TYPE_WEIGHT = 25
_SUBDIRECTORY_ORGANIZATION_WEIGHT = 25
_DOMINANT_LANGUAGE_WEIGHT = 25
_HAS_SOURCE_CONTENT_WEIGHT = 25
_DOMINANT_LANGUAGE_THRESHOLD_PERCENT = 40.0

# --- Maintainability Score weights (sum to 100) ---
_FILE_SIZE_WEIGHT = 40
_DIRECTORY_DEPTH_WEIGHT = 30
_FILES_PER_DIRECTORY_WEIGHT = 30
_HEALTHY_AVG_LINES_MIN = 20
_HEALTHY_AVG_LINES_MAX = 400
_HEALTHY_FILES_PER_DIRECTORY = 15


class CodebaseAnalyzer:
    """Computes the Codebase Score and Maintainability Score from Module 3's output."""

    def analyze_codebase(self, static_analysis_result: StaticAnalysisResult) -> SubScore:
        """Score directory organization, project structure, and language cohesion (0-100)."""
        evidence: List[str] = []
        reasons: List[str] = []
        score = 0.0

        if static_analysis_result.project_types:
            score += _PROJECT_TYPE_WEIGHT
            evidence.append(
                f"Detected project type(s): {', '.join(static_analysis_result.project_types)}."
            )
        else:
            evidence.append("No recognized project type/configuration file detected.")
            reasons.append(f"No detected project type (-{_PROJECT_TYPE_WEIGHT} pts).")

        if static_analysis_result.total_directories > 0:
            score += _SUBDIRECTORY_ORGANIZATION_WEIGHT
            evidence.append(
                f"Repository uses {static_analysis_result.total_directories} subdirectories for organization."
            )
        else:
            evidence.append("Repository has no subdirectories; all files are at the root.")
            reasons.append(f"Flat, unorganized structure (-{_SUBDIRECTORY_ORGANIZATION_WEIGHT} pts).")

        top_language_percentage = self._top_language_percentage(static_analysis_result)
        if top_language_percentage >= _DOMINANT_LANGUAGE_THRESHOLD_PERCENT:
            score += _DOMINANT_LANGUAGE_WEIGHT
            evidence.append(f"Clear dominant language at {top_language_percentage:.1f}% of source files.")
        else:
            evidence.append(f"No clear dominant language (top language at {top_language_percentage:.1f}%).")
            reasons.append(f"Fragmented language distribution (-{_DOMINANT_LANGUAGE_WEIGHT} pts).")

        if static_analysis_result.supported_source_files > 1:
            score += _HAS_SOURCE_CONTENT_WEIGHT
            evidence.append(
                f"{static_analysis_result.supported_source_files} recognized source files present."
            )
        else:
            evidence.append("Fewer than two recognized source files present.")
            reasons.append(f"Little to no source content (-{_HAS_SOURCE_CONTENT_WEIGHT} pts).")

        logger.debug("Codebase score computed: %.2f", score)
        return SubScore(score=round(score, 2), evidence=evidence, reasons=reasons)

    def analyze_maintainability(self, static_analysis_result: StaticAnalysisResult) -> SubScore:
        """Score average file size, directory depth, and files-per-directory balance (0-100)."""
        evidence: List[str] = []
        reasons: List[str] = []
        score = 0.0

        avg_lines_per_file = self._average_lines_per_file(static_analysis_result)
        if avg_lines_per_file is None:
            evidence.append("No supported source files to measure average file size.")
            reasons.append(f"No source files to assess file size (-{_FILE_SIZE_WEIGHT} pts).")
        elif _HEALTHY_AVG_LINES_MIN <= avg_lines_per_file <= _HEALTHY_AVG_LINES_MAX:
            score += _FILE_SIZE_WEIGHT
            evidence.append(f"Average file size is {avg_lines_per_file:.1f} lines (healthy range).")
        elif avg_lines_per_file > _HEALTHY_AVG_LINES_MAX:
            score += _FILE_SIZE_WEIGHT * 0.4
            evidence.append(f"Average file size is {avg_lines_per_file:.1f} lines (large files detected).")
            reasons.append(f"Large average file size may hinder maintainability (-{_FILE_SIZE_WEIGHT * 0.6:.0f} pts).")
        else:
            score += _FILE_SIZE_WEIGHT * 0.6
            evidence.append(f"Average file size is {avg_lines_per_file:.1f} lines (very small files).")
            reasons.append(f"Very small average file size may indicate over-fragmentation (-{_FILE_SIZE_WEIGHT * 0.4:.0f} pts).")

        depth = max_tree_depth(static_analysis_result.directory_tree)
        if depth >= 2:
            score += _DIRECTORY_DEPTH_WEIGHT
            evidence.append(f"Directory tree has meaningful nesting (observed depth: {depth}).")
        elif depth == 1:
            score += _DIRECTORY_DEPTH_WEIGHT * 0.4
            evidence.append("Directory tree has minimal nesting (root-level files only, one level of files/dirs).")
            reasons.append(f"Minimal directory structure (-{_DIRECTORY_DEPTH_WEIGHT * 0.6:.0f} pts).")
        else:
            evidence.append("Directory tree has no nesting (empty repository).")
            reasons.append(f"No directory structure (-{_DIRECTORY_DEPTH_WEIGHT} pts).")

        files_per_directory = self._files_per_directory(static_analysis_result)
        if files_per_directory <= _HEALTHY_FILES_PER_DIRECTORY:
            score += _FILES_PER_DIRECTORY_WEIGHT
            evidence.append(f"Average of {files_per_directory:.1f} files per directory (balanced).")
        else:
            partial = max(_FILES_PER_DIRECTORY_WEIGHT * (_HEALTHY_FILES_PER_DIRECTORY / files_per_directory), 0)
            score += partial
            evidence.append(f"Average of {files_per_directory:.1f} files per directory (files concentrated).")
            reasons.append(f"High files-per-directory ratio (-{_FILES_PER_DIRECTORY_WEIGHT - partial:.0f} pts).")

        logger.debug("Maintainability score computed: %.2f", score)
        return SubScore(score=round(min(score, 100.0), 2), evidence=evidence, reasons=reasons)

    @staticmethod
    def _top_language_percentage(static_analysis_result: StaticAnalysisResult) -> float:
        if not static_analysis_result.language_distribution:
            return 0.0
        return max(entry.percentage for entry in static_analysis_result.language_distribution)

    @staticmethod
    def _average_lines_per_file(static_analysis_result: StaticAnalysisResult) -> float | None:
        if static_analysis_result.supported_source_files == 0:
            return None
        return static_analysis_result.total_lines / static_analysis_result.supported_source_files

    @staticmethod
    def _files_per_directory(static_analysis_result: StaticAnalysisResult) -> float:
        directories = max(static_analysis_result.total_directories, 1)
        return static_analysis_result.total_files / directories
