"""
RepositoryScanner — Module 3 component.

Walks a local repository directory tree (without ever executing any of
its contents), applying the configured ignore rules, and produces:
    - the flat list of files and directories encountered
    - a shallow, depth- and entry-limited directory tree for display

No line counting or language detection happens here — this component is
concerned only with filesystem traversal.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

from app.core.exceptions import RepositoryPathNotFoundError
from app.schemas.static_analysis import DirectoryTreeNode

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Raw filesystem traversal result, prior to language/line analysis."""

    root: Path
    files: List[Path] = field(default_factory=list)
    directories: List[Path] = field(default_factory=list)
    directory_tree: DirectoryTreeNode = None  # type: ignore[assignment]


class RepositoryScanner:
    """Traverses a repository directory, honoring configured ignore rules."""

    def __init__(
        self,
        ignored_directories: List[str],
        tree_max_depth: int,
        tree_max_entries_per_level: int,
    ) -> None:
        self._ignored: Set[str] = set(ignored_directories)
        self._tree_max_depth = tree_max_depth
        self._tree_max_entries = tree_max_entries_per_level

    def scan(self, root: Path) -> ScanResult:
        """
        Walk `root`, skipping ignored directories, and collect files/directories.

        Raises:
            RepositoryPathNotFoundError: If `root` does not exist or is not a directory.
        """
        if not root.exists() or not root.is_dir():
            raise RepositoryPathNotFoundError(
                f"Local repository path '{root}' does not exist or is not a directory. "
                "Ensure the repository has been cloned via Module 2 first."
            )

        files: List[Path] = []
        directories: List[Path] = []

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune ignored directories in-place so os.walk does not descend into them.
            dirnames[:] = sorted(d for d in dirnames if d not in self._ignored)

            current_dir = Path(dirpath)
            if current_dir != root:
                directories.append(current_dir)

            for filename in filenames:
                files.append(current_dir / filename)

        logger.info(
            "Scanned %s: %d files, %d directories (ignored: %s)",
            root,
            len(files),
            len(directories),
            sorted(self._ignored),
        )

        directory_tree = self._build_tree(root, depth=0)
        return ScanResult(root=root, files=files, directories=directories, directory_tree=directory_tree)

    def _build_tree(self, path: Path, depth: int) -> DirectoryTreeNode:
        """Recursively build a depth- and entry-limited directory tree node."""
        try:
            entries = [
                entry
                for entry in path.iterdir()
                if not (entry.is_dir() and entry.name in self._ignored)
            ]
        except OSError as exc:
            logger.warning("Unable to list directory %s: %s", path, exc)
            entries = []

        # Directories first, then files, both alphabetically.
        entries.sort(key=lambda entry: (entry.is_file(), entry.name.lower()))

        node_name = path.name or str(path)

        if depth >= self._tree_max_depth:
            return DirectoryTreeNode(
                name=node_name, type="directory", children=None, truncated=len(entries) > 0
            )

        children: List[DirectoryTreeNode] = []
        truncated = False
        for index, entry in enumerate(entries):
            if index >= self._tree_max_entries:
                truncated = True
                break
            if entry.is_dir():
                children.append(self._build_tree(entry, depth + 1))
            else:
                children.append(DirectoryTreeNode(name=entry.name, type="file"))

        return DirectoryTreeNode(name=node_name, type="directory", children=children, truncated=truncated)
