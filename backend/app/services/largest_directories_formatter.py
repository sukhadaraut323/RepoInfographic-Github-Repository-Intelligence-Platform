"""
LargestDirectoriesFormatter — Module 6 component.

Aggregates file counts per top-level directory directly from Module 3's
already-produced `directory_tree` — no filesystem access, and no new
scanning. Reuses the existing `flatten_tree` helper (introduced for
Module 5) unchanged.

Because Module 3's tree is itself depth- and entry-limited, these counts
are bounded by whatever Module 3 already captured — the same documented
trade-off Module 5's tree-based checks rely on.
"""

import logging
from typing import List

from app.schemas.analytics import LargestDirectoryEntry
from app.schemas.static_analysis import StaticAnalysisResult
from app.utils.directory_tree_utils import flatten_tree

logger = logging.getLogger(__name__)


class LargestDirectoriesFormatter:
    """Formats the largest top-level directories (by file count) for a bar chart."""

    def __init__(self, limit: int) -> None:
        self._limit = limit

    def format(self, static_analysis_result: StaticAnalysisResult) -> List[LargestDirectoryEntry]:
        """Return the top-level directories with the most files, largest first."""
        root = static_analysis_result.directory_tree
        top_level_directories = [child.name for child in (root.children or []) if child.type == "directory"]

        if not top_level_directories:
            return []

        file_counts = {name: 0 for name in top_level_directories}
        for path, entry_type in flatten_tree(root):
            if entry_type != "file":
                continue
            top_segment = path.split("/", 1)[0]
            if top_segment in file_counts:
                file_counts[top_segment] += 1

        entries = [
            LargestDirectoryEntry(name=name, path=name, file_count=count)
            for name, count in file_counts.items()
        ]
        entries.sort(key=lambda entry: entry.file_count, reverse=True)

        logger.debug("Formatted %d largest-directory entries", len(entries))
        return entries[: self._limit]
