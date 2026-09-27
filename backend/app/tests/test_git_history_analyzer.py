"""
Integration tests for `GitHistoryAnalyzer`.

These tests exercise real GitPython/git operations against temporary
local repositories — no mocking, no network access required.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from git import Repo

from app.core.exceptions import (
    GitHistoryAnalysisError,
    NotAGitRepositoryError,
    RepositoryPathNotFoundError,
)
from app.services.git_history_analyzer import GitHistoryAnalyzer


def _make_commit(repo: Repo, filename: str, content: str, message: str) -> None:
    repo_path = Path(repo.working_dir)
    (repo_path / filename).write_text(content)
    repo.index.add([filename])
    repo.index.commit(message)


@pytest.fixture
def analyzer() -> GitHistoryAnalyzer:
    return GitHistoryAnalyzer()


def test_open_repository_raises_for_missing_path(analyzer, tmp_path) -> None:
    with pytest.raises(RepositoryPathNotFoundError):
        analyzer.open_repository(tmp_path / "does_not_exist")


def test_open_repository_raises_for_non_git_directory(analyzer, tmp_path) -> None:
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    with pytest.raises(NotAGitRepositoryError):
        analyzer.open_repository(plain_dir)


def test_open_repository_succeeds_for_valid_repo(analyzer, tmp_path) -> None:
    Repo.init(str(tmp_path), initial_branch="main")
    repo = analyzer.open_repository(tmp_path)
    assert repo is not None


def test_get_commits_returns_empty_list_for_empty_repo(analyzer, tmp_path) -> None:
    Repo.init(str(tmp_path), initial_branch="main")
    repo = analyzer.open_repository(tmp_path)

    commits = analyzer.get_commits(repo)

    assert commits == []


def test_get_commits_returns_all_commits(analyzer, tmp_path) -> None:
    repo = Repo.init(str(tmp_path), initial_branch="main")
    _make_commit(repo, "a.txt", "1", "first commit")
    _make_commit(repo, "b.txt", "2", "second commit")

    commits = analyzer.get_commits(repo)

    assert len(commits) == 2
    messages_authors = {c.author_email for c in commits}
    assert len(messages_authors) == 1  # same git identity for both commits in test env


def test_get_commits_raises_on_corrupted_metadata(analyzer, tmp_path) -> None:
    repo = Repo.init(str(tmp_path), initial_branch="main")
    _make_commit(repo, "a.txt", "1", "first commit")

    # Corrupt HEAD to simulate unreadable/corrupted git metadata.
    head_path = tmp_path / ".git" / "HEAD"
    head_path.write_text("this is not a valid ref\n")

    with pytest.raises(GitHistoryAnalysisError):
        analyzer.get_commits(repo)


def test_get_branch_names_local_only_repo(analyzer, tmp_path) -> None:
    repo = Repo.init(str(tmp_path), initial_branch="main")
    _make_commit(repo, "a.txt", "1", "first commit")
    repo.git.branch("develop")

    branch_names = analyzer.get_branch_names(repo)

    assert set(branch_names) == {"main", "develop"}


def test_get_default_branch_from_active_branch(analyzer, tmp_path) -> None:
    repo = Repo.init(str(tmp_path), initial_branch="main")
    _make_commit(repo, "a.txt", "1", "first commit")

    branch_names = analyzer.get_branch_names(repo)
    default_branch = analyzer.get_default_branch(repo, branch_names)

    assert default_branch == "main"


def test_get_default_branch_falls_back_when_no_branches(analyzer, tmp_path) -> None:
    Repo.init(str(tmp_path), initial_branch="main")
    repo = analyzer.open_repository(tmp_path)

    # No commits => no real refs exist yet, but active_branch still resolves
    # to the symbolic default name in GitPython/git.
    branch_names = analyzer.get_branch_names(repo)
    default_branch = analyzer.get_default_branch(repo, branch_names)

    assert default_branch == "main"
