"""
Shared test-fixture factories for Module 5 tests.

Builds minimal-but-valid instances of Modules 1, 3, and 4's output
schemas, so each Module 5 test can focus on the specific fields it cares
about without repeating all the required boilerplate fields.
"""

from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.git_history import ActivityLevel, GitHistoryResult
from app.schemas.repository import RepositoryMetadata, RepositoryOwner
from app.schemas.static_analysis import DirectoryTreeNode, LanguageDistributionEntry, StaticAnalysisResult


def make_repository_metadata(
    *,
    full_name: str = "octo/demo",
    stargazers_count: int = 0,
    forks_count: int = 0,
    watchers_count: int = 0,
    open_issues_count: int = 0,
) -> RepositoryMetadata:
    return RepositoryMetadata(
        full_name=full_name,
        owner=RepositoryOwner(login=full_name.split("/")[0], type="Organization"),
        description="A demo repository.",
        html_url=f"https://github.com/{full_name}",
        default_branch="main",
        visibility="public",
        is_archived=False,
        is_fork=False,
        stargazers_count=stargazers_count,
        forks_count=forks_count,
        watchers_count=watchers_count,
        open_issues_count=open_issues_count,
        size_kb=100,
        license_name="MIT License",
        topics=[],
        primary_language="Python",
        languages={"Python": 1000},
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def make_directory_tree(name: str = "demo", children: Optional[List[DirectoryTreeNode]] = None) -> DirectoryTreeNode:
    return DirectoryTreeNode(name=name, type="directory", children=children or [])


def file_node(name: str) -> DirectoryTreeNode:
    return DirectoryTreeNode(name=name, type="file")


def dir_node(name: str, children: Optional[List[DirectoryTreeNode]] = None) -> DirectoryTreeNode:
    return DirectoryTreeNode(name=name, type="directory", children=children or [])


def make_static_analysis_result(
    *,
    local_path: str = "/workspace/octo_demo",
    total_files: int = 5,
    total_directories: int = 1,
    supported_source_files: int = 3,
    total_lines: int = 300,
    blank_lines: int = 30,
    comment_lines: int = 30,
    project_types: Optional[List[str]] = None,
    language_distribution: Optional[List[LanguageDistributionEntry]] = None,
    directory_tree: Optional[DirectoryTreeNode] = None,
) -> StaticAnalysisResult:
    return StaticAnalysisResult(
        local_path=local_path,
        total_files=total_files,
        total_directories=total_directories,
        supported_source_files=supported_source_files,
        language_distribution=language_distribution
        or [LanguageDistributionEntry(language="Python", file_count=supported_source_files, percentage=100.0)],
        total_lines=total_lines,
        blank_lines=blank_lines,
        comment_lines=comment_lines,
        project_types=project_types or [],
        directory_tree=directory_tree or make_directory_tree(),
        ignored_directories=[".git"],
        scanned_at=datetime.now(timezone.utc),
    )


def make_git_history_result(
    *,
    local_path: str = "/workspace/octo_demo",
    repository_age_days: int = 400,
    total_commits: int = 50,
    unique_contributors: int = 3,
    total_branches: int = 1,
    default_branch: Optional[str] = "main",
    average_commits_per_day: float = 0.5,
    average_commits_per_week: float = 3.5,
    average_commits_per_month: float = 15.0,
    recent_activity_level: ActivityLevel = ActivityLevel.MEDIUM,
) -> GitHistoryResult:
    return GitHistoryResult(
        local_path=local_path,
        repository_age_days=repository_age_days,
        first_commit_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        latest_commit_date=datetime.now(timezone.utc),
        total_commits=total_commits,
        unique_contributors=unique_contributors,
        total_branches=total_branches,
        default_branch=default_branch,
        average_commits_per_day=average_commits_per_day,
        average_commits_per_week=average_commits_per_week,
        average_commits_per_month=average_commits_per_month,
        monthly_commit_timeline=[],
        recent_activity_level=recent_activity_level,
        analyzed_at=datetime.now(timezone.utc),
    )
