"""Unit tests for app.services.repository_cloner_service.RepositoryClonerService."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.schemas.clone_result import CloneStatus
from app.services.repository_cloner_service import RepositoryClonerService


def _make_settings(workspace_directory: str) -> Settings:
    return Settings(github_token="dummy-token", workspace_directory=workspace_directory)


@pytest.fixture
def mock_git_client() -> MagicMock:
    return MagicMock()


def test_clone_or_update_clones_when_local_path_missing(mock_git_client, tmp_path) -> None:
    settings = _make_settings(str(tmp_path))
    mock_git_client.get_active_branch_name.return_value = "main"
    mock_git_client.get_last_commit_datetime.return_value = datetime.now(timezone.utc)
    mock_git_client.clone_with_recovery.return_value = MagicMock()

    service = RepositoryClonerService(git_client=mock_git_client, settings=settings)
    result = service.clone_or_update_repository("https://github.com/fastapi/fastapi")

    expected_path = tmp_path / "fastapi_fastapi"
    mock_git_client.clone_with_recovery.assert_called_once()
    call_args = mock_git_client.clone_with_recovery.call_args
    assert call_args.args[0] == "https://github.com/fastapi/fastapi.git"
    assert call_args.args[1] == expected_path
    assert call_args.args[2] is None  # branch
    # The service passes its retry/transport settings straight through, not hardcoded values.
    assert call_args.kwargs["max_attempts"] == settings.clone_max_attempts
    assert call_args.kwargs["post_buffer_bytes"] == settings.clone_http_post_buffer_bytes
    assert call_args.kwargs["partial_clone_fallback_enabled"] == settings.clone_partial_clone_fallback_enabled

    assert result.status == CloneStatus.CLONED
    assert result.owner == "fastapi"
    assert result.repository == "fastapi"
    assert result.local_path == str(expected_path)


def test_clone_or_update_updates_when_local_path_exists_and_stale(mock_git_client, tmp_path) -> None:
    settings = _make_settings(str(tmp_path))
    existing_path = tmp_path / "fastapi_fastapi"
    existing_path.mkdir(parents=True)

    fake_repo = MagicMock()
    mock_git_client.open_existing.return_value = fake_repo
    mock_git_client.get_active_branch_name.return_value = "main"
    mock_git_client.is_up_to_date.return_value = False
    mock_git_client.get_last_commit_datetime.return_value = datetime.now(timezone.utc)

    service = RepositoryClonerService(git_client=mock_git_client, settings=settings)
    result = service.clone_or_update_repository("https://github.com/fastapi/fastapi")

    mock_git_client.open_existing.assert_called_once_with(existing_path)
    mock_git_client.fetch.assert_called_once_with(fake_repo)
    mock_git_client.pull.assert_called_once_with(fake_repo, "main")
    assert result.status == CloneStatus.UPDATED


def test_clone_or_update_reports_already_exists_when_up_to_date(mock_git_client, tmp_path) -> None:
    settings = _make_settings(str(tmp_path))
    existing_path = tmp_path / "fastapi_fastapi"
    existing_path.mkdir(parents=True)

    fake_repo = MagicMock()
    mock_git_client.open_existing.return_value = fake_repo
    mock_git_client.get_active_branch_name.return_value = "main"
    mock_git_client.is_up_to_date.return_value = True
    mock_git_client.get_last_commit_datetime.return_value = datetime.now(timezone.utc)

    service = RepositoryClonerService(git_client=mock_git_client, settings=settings)
    result = service.clone_or_update_repository("https://github.com/fastapi/fastapi")

    mock_git_client.pull.assert_not_called()
    assert result.status == CloneStatus.ALREADY_EXISTS


def test_clone_or_update_checks_out_requested_branch_on_existing_repo(mock_git_client, tmp_path) -> None:
    settings = _make_settings(str(tmp_path))
    existing_path = tmp_path / "fastapi_fastapi"
    existing_path.mkdir(parents=True)

    fake_repo = MagicMock()
    mock_git_client.open_existing.return_value = fake_repo
    mock_git_client.get_active_branch_name.return_value = "main"
    mock_git_client.is_up_to_date.return_value = True
    mock_git_client.get_last_commit_datetime.return_value = datetime.now(timezone.utc)

    service = RepositoryClonerService(git_client=mock_git_client, settings=settings)
    result = service.clone_or_update_repository(
        "https://github.com/fastapi/fastapi", branch="develop"
    )

    mock_git_client.checkout.assert_called_once_with(fake_repo, "develop")
    assert result.branch == "develop"


def test_workspace_directory_is_created_if_missing(mock_git_client, tmp_path) -> None:
    workspace_dir = tmp_path / "nested" / "workspace"
    settings = _make_settings(str(workspace_dir))
    mock_git_client.get_active_branch_name.return_value = "main"
    mock_git_client.get_last_commit_datetime.return_value = datetime.now(timezone.utc)

    service = RepositoryClonerService(git_client=mock_git_client, settings=settings)
    service.clone_or_update_repository("https://github.com/fastapi/fastapi")

    assert workspace_dir.exists()
