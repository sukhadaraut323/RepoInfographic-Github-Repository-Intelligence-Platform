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


# ---------------------------------------------------------------------------
# clone_with_recovery: automatic retry, transient/permanent classification,
# partial-directory cleanup, and the blobless partial-clone fallback.
#
# `Repo.clone_from` itself is patched for these (rather than a real flaky
# network), since reliably reproducing a real mid-transfer TCP reset is not
# practical in a test environment - what's under test is this client's own
# retry/classification/cleanup logic, not GitPython's or git's transport.
# `is_transient_clone_error` (the classifier) is exercised directly, and
# separately, against real GitCommandError-shaped stderr text.
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, call, patch

from git import GitCommandError

from app.clients.git_client import is_transient_clone_error


def _recovery_kwargs(**overrides):
    base = dict(
        max_attempts=3,
        backoff_seconds=0.0,  # no real sleep in tests
        post_buffer_bytes=524_288_000,
        low_speed_limit_bytes=1000,
        low_speed_time_seconds=30,
        partial_clone_fallback_enabled=True,
    )
    base.update(overrides)
    return base


def _transient_error(message: str = "RPC failed; curl 56 Recv failure: Connection was reset") -> GitCommandError:
    return GitCommandError(["git", "clone"], 128, stderr=message)


def _permanent_error(message: str = "repository 'https://github.com/x/y.git/' not found") -> GitCommandError:
    return GitCommandError(["git", "clone"], 128, stderr=message)


@pytest.mark.parametrize(
    "stderr",
    [
        "RPC failed; curl 56 Recv failure: Connection was reset",
        "fatal: early EOF",
        "fatal: fetch-pack: invalid index-pack output",
        "fatal: the remote end hung up unexpectedly",
        "Operation timed out",
        "Could not resolve host: github.com",
    ],
)
def test_is_transient_clone_error_recognizes_real_transport_failures(stderr) -> None:
    assert is_transient_clone_error(GitCommandError(["git"], 128, stderr=stderr)) is True


@pytest.mark.parametrize(
    "stderr",
    [
        "repository 'https://github.com/owner/missing.git/' not found",
        "remote: Repository not found.",
        "fatal: Authentication failed for 'https://github.com/owner/private.git/'",
        "fatal: could not read Username for 'https://github.com': terminal prompts disabled",
    ],
)
def test_is_transient_clone_error_does_not_retry_permanent_failures(stderr) -> None:
    assert is_transient_clone_error(GitCommandError(["git"], 128, stderr=stderr)) is False


def test_clone_with_recovery_succeeds_on_first_attempt_when_clone_works(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"

    repo = git_client.clone_with_recovery(source_repo.working_dir, destination, None, **_recovery_kwargs())

    assert destination.exists()
    assert (destination / "README.md").exists()
    assert git_client.get_active_branch_name(repo) == "main"


def test_clone_with_recovery_retries_transient_failure_then_succeeds(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    real_clone_from = Repo.clone_from
    attempts = []

    def flaky_clone_from(*args, **kwargs):
        attempts.append(1)
        if len(attempts) < 3:
            raise _transient_error()
        return real_clone_from(*args, **kwargs)

    with patch("app.clients.git_client.Repo.clone_from", side_effect=flaky_clone_from):
        repo = git_client.clone_with_recovery(
            source_repo.working_dir, destination, None, **_recovery_kwargs(max_attempts=3)
        )

    assert len(attempts) == 3  # failed twice, succeeded on the 3rd
    assert destination.exists() and (destination / "README.md").exists()
    assert git_client.get_active_branch_name(repo) == "main"


def test_clone_with_recovery_does_not_retry_a_permanent_failure(git_client, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    call_count = []

    def always_permanent(*args, **kwargs):
        call_count.append(1)
        raise _permanent_error()

    with patch("app.clients.git_client.Repo.clone_from", side_effect=always_permanent):
        with pytest.raises(RepositoryCloneError):
            git_client.clone_with_recovery(
                "https://github.com/owner/missing.git", destination, None, **_recovery_kwargs(max_attempts=3)
            )

    assert len(call_count) == 1  # no retries, no fallback attempt
    assert not destination.exists()  # cleaned up, never left as a fake "valid" workspace


def test_clone_with_recovery_cleans_a_leftover_partial_directory_before_retrying(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    destination.mkdir()
    (destination / "partial-garbage.txt").write_text("leftover from a previous failed attempt")

    repo = git_client.clone_with_recovery(source_repo.working_dir, destination, None, **_recovery_kwargs())

    assert not (destination / "partial-garbage.txt").exists()  # wiped, not merged into
    assert (destination / "README.md").exists()  # real clone succeeded


def test_clone_with_recovery_falls_back_to_partial_clone_after_exhausting_retries(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    real_clone_from = Repo.clone_from
    calls = []

    def fail_full_clone_succeed_on_partial(*args, **kwargs):
        calls.append(kwargs.get("filter"))
        if kwargs.get("filter") == "blob:none":
            return real_clone_from(*args, **kwargs)
        raise _transient_error()

    with patch("app.clients.git_client.Repo.clone_from", side_effect=fail_full_clone_succeed_on_partial):
        repo = git_client.clone_with_recovery(
            source_repo.working_dir, destination, None, **_recovery_kwargs(max_attempts=2)
        )

    assert calls == [None, None, "blob:none"]  # 2 full-clone attempts, then the partial-clone fallback
    assert (destination / "README.md").exists()  # history-preserving fallback still produced a working checkout
    assert git_client.get_active_branch_name(repo) == "main"


def test_clone_with_recovery_fallback_disabled_raises_after_retries_exhausted(git_client, tmp_path) -> None:
    destination = tmp_path / "clone_target"

    with patch("app.clients.git_client.Repo.clone_from", side_effect=lambda *a, **k: (_ for _ in ()).throw(_transient_error())):
        with pytest.raises(RepositoryCloneError):
            git_client.clone_with_recovery(
                "https://github.com/owner/flaky.git", destination, None,
                **_recovery_kwargs(max_attempts=2, partial_clone_fallback_enabled=False),
            )

    assert not destination.exists()


def test_clone_with_recovery_raises_when_fallback_also_fails(git_client, tmp_path) -> None:
    destination = tmp_path / "clone_target"

    with patch("app.clients.git_client.Repo.clone_from", side_effect=lambda *a, **k: (_ for _ in ()).throw(_transient_error())):
        with pytest.raises(RepositoryCloneError):
            git_client.clone_with_recovery(
                "https://github.com/owner/very-flaky.git", destination, None,
                **_recovery_kwargs(max_attempts=2, partial_clone_fallback_enabled=True),
            )

    assert not destination.exists()  # cleaned up even after the fallback also failed


def test_clone_with_recovery_passes_tuned_transport_config(git_client, source_repo, tmp_path) -> None:
    destination = tmp_path / "clone_target"
    seen_kwargs = {}
    real_clone_from = Repo.clone_from

    def capture(*args, **kwargs):
        seen_kwargs.update(kwargs)
        return real_clone_from(*args, **kwargs)

    with patch("app.clients.git_client.Repo.clone_from", side_effect=capture):
        git_client.clone_with_recovery(
            source_repo.working_dir, destination, None,
            **_recovery_kwargs(post_buffer_bytes=123, low_speed_limit_bytes=456, low_speed_time_seconds=7),
        )

    assert seen_kwargs["allow_unsafe_options"] is True
    assert "-c http.postBuffer=123" in seen_kwargs["multi_options"]
    assert "-c http.lowSpeedLimit=456" in seen_kwargs["multi_options"]
    assert "-c http.lowSpeedTime=7" in seen_kwargs["multi_options"]


def test_clone_with_recovery_respects_requested_branch(git_client, tmp_path) -> None:
    source_path = tmp_path / "source_repo_dev"
    repo = _init_source_repo(source_path, branch="main")
    repo.git.checkout("-b", "develop")
    (source_path / "dev.txt").write_text("dev branch file\n")
    repo.index.add(["dev.txt"])
    repo.index.commit("Dev branch commit")

    destination = tmp_path / "clone_target"
    git_client.clone_with_recovery(str(source_path), destination, "develop", **_recovery_kwargs())

    assert git_client.get_active_branch_name(git_client.open_existing(destination)) == "develop"
    assert (destination / "dev.txt").exists()
