"""
FileTypeDistributionFormatter — Module 6 component.

Splits Module 3's `total_files` into two broad categories — recognized
source files vs. everything else — using only subtraction over fields
Module 3 already computed. Distinct from Language Distribution (which
breaks supported source files down by specific language): this shows the
overall share of the repository that is recognized source code at all.
"""

import logging
from typing import List

from app.schemas.analytics import FileTypeDistributionSlice
from app.schemas.static_analysis import StaticAnalysisResult

logger = logging.getLogger(__name__)


class FileTypeDistributionFormatter:
    """Formats a broad source-vs-other file split from Module 3's totals."""

    def format(self, static_analysis_result: StaticAnalysisResult) -> List[FileTypeDistributionSlice]:
        """Return a two-slice source/other breakdown, or an empty list if there are no files."""
        total_files = static_analysis_result.total_files
        if total_files == 0:
            return []

        source_files = static_analysis_result.supported_source_files
        other_files = total_files - source_files

        slices = [
            FileTypeDistributionSlice(
                name="Source Files",
                value=source_files,
                percentage=round((source_files / total_files) * 100, 2),
            ),
            FileTypeDistributionSlice(
                name="Other Files",
                value=other_files,
                percentage=round((other_files / total_files) * 100, 2),
            ),
        ]
        logger.debug("Formatted file type distribution: %d source, %d other", source_files, other_files)
        return slices
