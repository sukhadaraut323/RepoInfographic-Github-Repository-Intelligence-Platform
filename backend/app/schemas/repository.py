"""
Pydantic schemas for Module 1 — GitHub Repository Metadata Collector.

`RepositoryMetadata` is the single contract returned by this module. It
intentionally contains only data sourced directly from the GitHub REST
API (`GET /repos/{owner}/{repo}` and `GET /repos/{owner}/{repo}/languages`).
No derived or computed metrics belong here — that responsibility sits with
later modules (Analytics Engine, Health Score, etc.).
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class RepositoryAnalyzeRequest(BaseModel):
    """Request body for POST /api/v1/repository/analyze."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository URL.",
        examples=["https://github.com/fastapi/fastapi"],
        min_length=1,
    )


class RepositoryOwner(BaseModel):
    """Minimal owner information as returned by GitHub."""

    login: str = Field(..., description="Owner's GitHub username or organization name.")
    type: str = Field(..., description='Owner type, e.g. "User" or "Organization".')
    avatar_url: Optional[HttpUrl] = Field(default=None, description="Owner's avatar image URL.")


class RepositoryMetadata(BaseModel):
    """
    Repository metadata and language breakdown collected from the
    GitHub REST API. This is the sole output contract of Module 1.
    """

    full_name: str = Field(..., description='Repository full name, e.g. "owner/repo".')
    owner: RepositoryOwner = Field(..., description="Repository owner details.")
    description: Optional[str] = Field(default=None, description="Repository description.")
    html_url: HttpUrl = Field(..., description="Repository URL on GitHub.")
    default_branch: str = Field(..., description="Default branch name.")
    visibility: str = Field(..., description='Repository visibility, e.g. "public".')
    is_archived: bool = Field(..., description="Whether the repository is archived.")
    is_fork: bool = Field(..., description="Whether the repository is a fork.")

    stargazers_count: int = Field(..., ge=0, description="Number of stars.")
    forks_count: int = Field(..., ge=0, description="Number of forks.")
    watchers_count: int = Field(..., ge=0, description="Number of watchers.")
    open_issues_count: int = Field(..., ge=0, description="Number of open issues (includes PRs).")

    size_kb: int = Field(..., ge=0, description="Repository size in kilobytes, as reported by GitHub.")
    license_name: Optional[str] = Field(default=None, description="SPDX license name, if any.")
    topics: List[str] = Field(default_factory=list, description="Repository topics/tags.")

    primary_language: Optional[str] = Field(
        default=None, description="Primary language as reported by GitHub."
    )
    languages: Dict[str, int] = Field(
        default_factory=dict,
        description="Language breakdown in bytes of code, as reported by GitHub.",
    )

    created_at: datetime = Field(..., description="Repository creation timestamp.")
    updated_at: datetime = Field(..., description="Last metadata update timestamp.")
    pushed_at: Optional[datetime] = Field(default=None, description="Last push timestamp.")
