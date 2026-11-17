"""
Pydantic schemas for Module 2 — Repository Cloner.

Kept in a dedicated file (separate from `schemas/repository.py`, which is
owned by Module 1) so Module 1's accepted schema contract is never touched.

`RepositoryCloneResult` is the sole output contract of this module. It
reports only the outcome of the clone/update operation — no static
analysis, git history, or metrics data belongs here.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CloneStatus(str, Enum):
    """Outcome of a clone-or-update operation."""

    CLONED = "cloned"
    UPDATED = "updated"
    ALREADY_EXISTS = "already_exists"


class RepositoryCloneRequest(BaseModel):
    """Request body for POST /api/v1/repository/clone."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository URL.",
        examples=["https://github.com/fastapi/fastapi"],
        min_length=1,
    )
    branch: Optional[str] = Field(
        default=None,
        description=(
            "Branch to clone/checkout. Defaults to the repository's "
            "default branch when omitted."
        ),
        examples=["main"],
    )


class RepositoryCloneResult(BaseModel):
    """Result of cloning or updating a local working copy of a repository."""

    owner: str = Field(..., description="Repository owner (GitHub username or organization).")
    repository: str = Field(..., description="Repository name.")
    branch: str = Field(..., description="Branch that was checked out locally.")
    local_path: str = Field(..., description="Absolute or relative path to the local working copy.")
    status: CloneStatus = Field(..., description="Outcome of the operation.")
    last_updated: datetime = Field(
        ..., description="Timestamp of the latest local commit after the operation."
    )
