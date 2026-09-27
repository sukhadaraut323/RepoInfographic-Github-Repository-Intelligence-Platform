"""
Pydantic schemas for Module 3 — Static Code Analysis.

Kept in a dedicated file so Module 1's and Module 2's schema files remain
untouched. `StaticAnalysisResult` is the sole output contract of this
module. It reports only objective, directly-countable facts about the
repository's files (counts, extensions, line totals) — no complexity
scores, dependency graphs, or AI-derived content belong here.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class StaticAnalysisRequest(BaseModel):
    """Request body for POST /api/v1/repository/scan."""

    local_path: str = Field(
        ...,
        description=(
            "Local filesystem path to a previously cloned repository, "
            "as produced by Module 2 (RepositoryCloneResult.local_path)."
        ),
        examples=["workspace/fastapi_fastapi"],
        min_length=1,
    )


class LanguageDistributionEntry(BaseModel):
    """File-count share of a single detected language."""

    language: str = Field(..., description="Detected language name.")
    file_count: int = Field(..., ge=0, description="Number of files detected for this language.")
    percentage: float = Field(
        ..., ge=0, le=100, description="Share of supported source files, as a percentage."
    )


class DirectoryTreeNode(BaseModel):
    """A single node in the shallow directory tree."""

    name: str = Field(..., description="File or directory name.")
    type: Literal["file", "directory"] = Field(..., description="Node type.")
    children: Optional[List["DirectoryTreeNode"]] = Field(
        default=None, description="Child nodes, present only for directories within the depth limit."
    )
    truncated: bool = Field(
        default=False,
        description="True if this directory has additional entries not shown due to depth/entry limits.",
    )


DirectoryTreeNode.model_rebuild()


class StaticAnalysisResult(BaseModel):
    """
    Result of static, non-executing analysis of a cloned repository.

    All fields are objective counts derived directly from the filesystem —
    no complexity, dependency, security, or AI-derived data is included.
    """

    local_path: str = Field(..., description="Path to the repository that was analyzed.")

    total_files: int = Field(..., ge=0, description="Total number of files (excluding ignored directories).")
    total_directories: int = Field(
        ..., ge=0, description="Total number of directories (excluding ignored directories)."
    )
    supported_source_files: int = Field(
        ..., ge=0, description="Number of files with a recognized language/extension."
    )

    language_distribution: List[LanguageDistributionEntry] = Field(
        default_factory=list, description="File-count breakdown by detected language."
    )

    total_lines: int = Field(..., ge=0, description="Total lines across all supported source files.")
    blank_lines: int = Field(..., ge=0, description="Total blank lines across all supported source files.")
    comment_lines: int = Field(
        ..., ge=0, description="Total comment lines across all supported source files."
    )

    project_types: List[str] = Field(
        default_factory=list,
        description="Detected project types based on marker files (e.g. requirements.txt, package.json).",
    )

    directory_tree: DirectoryTreeNode = Field(
        ..., description="Shallow directory tree of the repository, depth- and entry-limited."
    )
    ignored_directories: List[str] = Field(
        default_factory=list, description="Directory names excluded from this scan."
    )

    scanned_at: datetime = Field(..., description="Timestamp when the scan was performed.")
