"""
Directory tree traversal utilities.

Shared by Module 5's analyzers so each one can look for marker files
(README, LICENSE, CI configs, etc.) directly on the `DirectoryTreeNode`
produced by Module 3 — without ever touching the filesystem again. This
is what lets Module 5 "consume the structured outputs produced by
previous modules" instead of rescanning the repository.

Because Module 3's tree is depth- and entry-limited (see
`static_analysis_tree_max_depth` / `static_analysis_tree_max_entries_per_level`),
lookups here are inherently bounded by whatever Module 3 already captured.
This is a deliberate, documented trade-off in exchange for not re-reading
the filesystem — deeply nested or numerous marker files beyond that
depth/entry limit will not be detected.
"""

from typing import List, Optional, Tuple

from app.schemas.static_analysis import DirectoryTreeNode


def flatten_tree(node: DirectoryTreeNode, prefix: str = "") -> List[Tuple[str, str]]:
    """
    Flatten a `DirectoryTreeNode` into a list of (relative_path, type) pairs.

    The root node itself is not included as a path entry — only its
    descendants are, with paths relative to the root using "/" separators.
    """
    entries: List[Tuple[str, str]] = []
    for child in node.children or []:
        child_path = f"{prefix}{child.name}"
        entries.append((child_path, child.type))
        if child.type == "directory":
            entries.extend(flatten_tree(child, prefix=f"{child_path}/"))
    return entries


def find_matching_path(
    node: DirectoryTreeNode,
    candidate_names: List[str],
    only_top_level: bool = False,
) -> Optional[str]:
    """
    Search the tree for a file/directory whose basename case-insensitively
    matches any of `candidate_names`, and return the first matching
    relative path found, or None.

    Args:
        node: Root of the tree to search (the repository root node).
        candidate_names: Exact basenames to match, case-insensitively
            (e.g. ["README.md", "README.rst", "README"]).
        only_top_level: If True, only the root's direct children are
            considered (useful for files conventionally kept at the
            repository root, like LICENSE or .gitignore).
    """
    lowered_candidates = {name.lower() for name in candidate_names}
    entries = (
        [(child.name, child.type) for child in (node.children or [])]
        if only_top_level
        else flatten_tree(node)
    )
    for path, _entry_type in entries:
        basename = path.rsplit("/", 1)[-1]
        if basename.lower() in lowered_candidates:
            return path
    return None


def directory_exists(node: DirectoryTreeNode, candidate_names: List[str]) -> Optional[str]:
    """
    Search the tree for a directory whose basename case-insensitively
    matches any of `candidate_names`, and return its relative path, or None.
    """
    lowered_candidates = {name.lower() for name in candidate_names}
    for path, entry_type in flatten_tree(node):
        if entry_type != "directory":
            continue
        basename = path.rsplit("/", 1)[-1]
        if basename.lower() in lowered_candidates:
            return path
    return None


def path_exists_with_suffix(node: DirectoryTreeNode, directory_prefix: str, suffixes: List[str]) -> bool:
    """
    Check whether any file exists under a directory path starting with
    `directory_prefix` (case-insensitive) whose name ends with one of
    `suffixes` (e.g. checking for any ".yml"/".yaml" file under ".github/workflows").
    """
    prefix_lower = directory_prefix.lower()
    lowered_suffixes = tuple(s.lower() for s in suffixes)
    for path, entry_type in flatten_tree(node):
        if entry_type != "file":
            continue
        if path.lower().startswith(prefix_lower) and path.lower().endswith(lowered_suffixes):
            return True
    return False


def max_tree_depth(node: DirectoryTreeNode, current_depth: int = 0) -> int:
    """
    Return the maximum depth observed in the tree (root = depth 0).

    Since the source tree itself is depth-limited by Module 3's
    configuration, this value is bounded by that same limit and should be
    interpreted as "at least this deep", not an exact repository-wide depth.
    """
    if not node.children:
        return current_depth
    return max(
        (
            max_tree_depth(child, current_depth + 1) if child.type == "directory" else current_depth + 1
            for child in node.children
        ),
        default=current_depth,
    )
