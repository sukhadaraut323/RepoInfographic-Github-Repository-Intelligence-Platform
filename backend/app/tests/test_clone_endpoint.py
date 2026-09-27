"""Integration tests for POST /api/v1/repository/clone."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.clone import get_repository_cloner_service
from app.core.exceptions import (
    InvalidGitReferenceError,
    InvalidRepositoryURLError,
    RepositoryCloneError,
)
from app.main import app
from app.schemas.clone_result import CloneStatus, RepositoryCloneResult

client = TestClient(app)

SAMPLE_RESULT = RepositoryCloneResult(
    owner="fastapi",
    repository="fastapi",
    branch="master",
    local_path="/workspace/fastapi_fastapi",
    status=CloneStatus.CLONED,
    last_updated=datetime.now(timezone.utc),
)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_clone_repository_success() -> None:
    mock_service = MagicMock()
    mock_service.clone_or_update_repository.return_value = SAMPLE_RESULT
    app.dependency_overrides[get_repository_cloner_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/clone",
        json={"repository_url": "https://github.com/fastapi/fastapi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["owner"] == "fastapi"
    assert body["repository"] == "fastapi"
    assert body["status"] == "cloned"
    assert body["local_path"] == "/workspace/fastapi_fastapi"


def test_clone_repository_passes_branch_through() -> None:
    mock_service = MagicMock()
    mock_service.clone_or_update_repository.return_value = SAMPLE_RESULT
    app.dependency_overrides[get_repository_cloner_service] = lambda: mock_service

    client.post(
        "/api/v1/repository/clone",
        json={"repository_url": "https://github.com/fastapi/fastapi", "branch": "develop"},
    )

    mock_service.clone_or_update_repository.assert_called_once_with(
        "https://github.com/fastapi/fastapi", "develop"
    )


def test_clone_repository_invalid_url_returns_400() -> None:
    mock_service = MagicMock()
    mock_service.clone_or_update_repository.side_effect = InvalidRepositoryURLError(
        "'not-a-url' is not a valid GitHub repository URL."
    )
    app.dependency_overrides[get_repository_cloner_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/clone",
        json={"repository_url": "not-a-url"},
    )

    assert response.status_code == 400


def test_clone_repository_invalid_branch_returns_400() -> None:
    mock_service = MagicMock()
    mock_service.clone_or_update_repository.side_effect = InvalidGitReferenceError(
        "Branch 'ghost-branch' does not exist on the remote."
    )
    app.dependency_overrides[get_repository_cloner_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/clone",
        json={"repository_url": "https://github.com/fastapi/fastapi", "branch": "ghost-branch"},
    )

    assert response.status_code == 400
    assert "ghost-branch" in response.json()["detail"]


def test_clone_repository_clone_failure_returns_502() -> None:
    mock_service = MagicMock()
    mock_service.clone_or_update_repository.side_effect = RepositoryCloneError(
        "Repository 'https://github.com/owner/private-repo' was not found or is not accessible."
    )
    app.dependency_overrides[get_repository_cloner_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/clone",
        json={"repository_url": "https://github.com/owner/private-repo"},
    )

    assert response.status_code == 502


def test_clone_repository_rejects_empty_url() -> None:
    response = client.post("/api/v1/repository/clone", json={"repository_url": ""})
    assert response.status_code == 422
