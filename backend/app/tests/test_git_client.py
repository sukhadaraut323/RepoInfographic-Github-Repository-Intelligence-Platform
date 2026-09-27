"""
Integration tests for `GitRepositoryClient`.

These tests exercise real GitPython/git operations end-to-end against a
temporary local repository acting as the "remote" (git supports cloning
from local filesystem paths, so no network access is required and no
GitPython internals are mocked here).
"""

from pathlib import Path

import pytest
from git import Repo

from app.clients.git_client import GitRepositoryClient
from app.core.exceptions import InvalidGitReferenceError, RepositoryCloneError


def _init_source_repo(path: Path, branch: str = "main") -> Repo:
    """Create a small local git repository with one commit on `branch`."""
    repo = Repo.init(str(path), initial_branch=branch)
    (path / "README.md").write_text("# test repo\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    return repo


def _commit_new_file(repo: Repo, filename: str, content: str) -> None:
    """Add a commit to an existing repo (simulates upstream changes)."""
    repo_path = Path(repo.working_dir)
    (repo_path / filename).write_text(content)
    repo.index.add([filename])
    repo.index.commit(f"Add {filename}")


@pytest.fixture
def source_repo(tmp_path: Path) -> Repo:
    source_path = tmp_path / "source_repo"
    return _init_source_repo(source_path)


@pytest.fixture
def git_client() -> GitRepositoryClient:
    return GitRepositoryClient()


def test_clone_creates_local_working_copy(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"

    cloned_repo = git_client.clone(source_repo.working_dir, destination)

    assert destination.exists()
    assert (destination / "README.md").exists()
    assert git_client.get_active_branch_name(cloned_repo) == "main"


def test_clone_nonexistent_remote_raises_clone_error(git_client, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    fake_remote = str(tmp_path / "does_not_exist")

    with pytest.raises(RepositoryCloneError):
        git_client.clone(fake_remote, destination)


def test_clone_with_invalid_branch_raises_reference_error(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"

    with pytest.raises(InvalidGitReferenceError):
        git_client.clone(source_repo.working_dir, destination, branch="does-not-exist")


def test_is_up_to_date_true_when_no_new_commits(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    cloned_repo = git_client.clone(source_repo.working_dir, destination)

    git_client.fetch(cloned_repo)

    assert git_client.is_up_to_date(cloned_repo, "main") is True


def test_pull_retrieves_new_upstream_commit(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    cloned_repo = git_client.clone(source_repo.working_dir, destination)

    # Simulate an upstream change after the clone was made.
    _commit_new_file(source_repo, "CHANGELOG.md", "v1.0.0\n")

    git_client.fetch(cloned_repo)
    assert git_client.is_up_to_date(cloned_repo, "main") is False

    git_client.pull(cloned_repo, "main")

    assert (destination / "CHANGELOG.md").exists()
    assert git_client.is_up_to_date(cloned_repo, "main") is True


def test_open_existing_returns_valid_repo(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    git_client.clone(source_repo.working_dir, destination)

    opened_repo = git_client.open_existing(destination)

    assert Path(opened_repo.working_dir) == destination


def test_open_existing_on_non_git_directory_raises_clone_error(git_client, tmp_path) -> None:
    plain_dir = tmp_path / "not_a_repo"
    plain_dir.mkdir()

    with pytest.raises(RepositoryCloneError):
        git_client.open_existing(plain_dir)


def test_get_last_commit_datetime_returns_datetime(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    cloned_repo = git_client.clone(source_repo.working_dir, destination)

    last_updated = git_client.get_last_commit_datetime(cloned_repo)

    assert last_updated is not None
