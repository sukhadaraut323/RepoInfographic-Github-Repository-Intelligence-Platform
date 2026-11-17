"""
LanguageDistributionFormatter — Module 6 component.

Reshapes Module 3's `language_distribution` (already-computed file
counts and percentages) into a Recharts-ready pie/bar chart shape.
No new counting or percentage computation happens here — only field
renaming, since Module 3's `LanguageDistributionEntry.file_count`
becomes the chart's `value` field.
"""

import logging
from typing import List

from app.schemas.analytics import LanguageDistributionSlice
from app.schemas.static_analysis import StaticAnalysisResult

logger = logging.getLogger(__name__)


class LanguageDistributionFormatter:
    """Formats Module 3's language distribution for chart consumption."""

    def format(self, static_analysis_result: StaticAnalysisResult) -> List[LanguageDistributionSlice]:
        """Return chart-ready language distribution slices, already sorted by Module 3."""
        slices = [
            LanguageDistributionSlice(
                name=entry.language,
                value=entry.file_count,
                percentage=entry.percentage,
            )
            for entry in static_analysis_result.language_distribution
        ]
        logger.debug("Formatted %d language distribution slices", len(slices))
        return slices
