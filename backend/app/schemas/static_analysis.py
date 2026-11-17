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


class RootMarkerFile(BaseModel):
    """A single well-known marker file's presence, detected from the complete
    (untruncated) file list rather than the depth/entry-limited display tree,
    so detection is reliable regardless of repository size."""

    present: bool = Field(..., description="Whether this file was found.")
    path: Optional[str] = Field(default=None, description="Relative path, if found.")


class RepositoryMarkerFiles(BaseModel):
    """Deterministic presence facts for well-known repository files.

    Computed directly from Module 3's complete file scan (not the display
    tree), so these are reliable even for repositories whose directory
    tree exceeds the display tree's depth/entry limits.
    """

    readme: RootMarkerFile
    license: RootMarkerFile
    contributing: RootMarkerFile
    changelog: RootMarkerFile
    dockerfile: RootMarkerFile
    docker_compose: RootMarkerFile
    gitignore: RootMarkerFile
    editorconfig: RootMarkerFile
    env_example: RootMarkerFile
    precommit_config: RootMarkerFile
    has_ci_config: bool = Field(..., description="CI config detected (GitHub Actions, Travis, CircleCI, GitLab CI, or Azure Pipelines).")
    has_docs_directory: bool = Field(..., description="A top-level docs/doc/documentation directory was found.")
    has_api_docs_tooling: bool = Field(..., description="API/reference doc tooling markers were found (mkdocs/sphinx/openapi/swagger config).")


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
        ..., description="Shallow directory tree of the repository, depth- and entry-limited. "
        "For reliable marker-file presence checks, use `marker_files` instead of searching this tree."
    )
    marker_files: RepositoryMarkerFiles = Field(
        ..., description="Deterministic presence facts for well-known files, from the complete file scan."
    )
    readme_content: Optional[str] = Field(
        default=None,
        description="The README's text content, if one was found and was readable text within the configured size cap. "
        "Null when no README exists or it could not be read as text.",
    )
    readme_truncated: bool = Field(
        default=False, description="True if readme_content was cut off at the configured character cap."
    )
    ignored_directories: List[str] = Field(
        default_factory=list, description="Directory names excluded from this scan."
    )

    scanned_at: datetime = Field(..., description="Timestamp when the scan was performed.")
