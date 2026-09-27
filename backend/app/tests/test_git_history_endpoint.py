"""Integration tests for POST /api/v1/repository/history."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.git_history import get_git_history_service
from app.core.exceptions import (
    GitHistoryAnalysisError,
    NotAGitRepositoryError,
    RepositoryPathNotFoundError,
)
from app.main import app
from app.schemas.git_history import ActivityLevel, GitHistoryResult

client = TestClient(app)

SAMPLE_RESULT = GitHistoryResult(
    local_path="/workspace/fastapi_fastapi",
    repository_age_days=1200,
    first_commit_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
    latest_commit_date=datetime.now(timezone.utc),
    total_commits=500,
    unique_contributors=42,
    total_branches=5,
    default_branch="main",
    average_commits_per_day=0.42,
    average_commits_per_week=2.94,
    average_commits_per_month=12.78,
    monthly_commit_timeline=[],
    recent_activity_level=ActivityLevel.HIGH,
    analyzed_at=datetime.now(timezone.utc),
)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_get_history_success() -> None:
    mock_service = MagicMock()
    mock_service.analyze.return_value = SAMPLE_RESULT
    app.dependency_overrides[get_git_history_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/history",
        json={"local_path": "/workspace/fastapi_fastapi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_commits"] == 500
    assert body["unique_contributors"] == 42
    assert body["recent_activity_level"] == "High"
    mock_service.analyze.assert_called_once_with("/workspace/fastapi_fastapi")


def test_get_history_path_not_found_returns_404() -> None:
    mock_service = MagicMock()
    mock_service.analyze.side_effect = RepositoryPathNotFoundError(
        "Local repository path '/workspace/missing' does not exist."
    )
    app.dependency_overrides[get_git_history_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/history",
        json={"local_path": "/workspace/missing"},
    )

    assert response.status_code == 404


def test_get_history_not_a_git_repo_returns_400() -> None:
    mock_service = MagicMock()
    mock_service.analyze.side_effect = NotAGitRepositoryError(
        "'/workspace/plain_dir' is not a valid git repository."
    )
    app.dependency_overrides[get_git_history_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/history",
        json={"local_path": "/workspace/plain_dir"},
    )

    assert response.status_code == 400


def test_get_history_analysis_error_returns_500() -> None:
    mock_service = MagicMock()
    mock_service.analyze.side_effect = GitHistoryAnalysisError("Corrupted git metadata.")
    app.dependency_overrides[get_git_history_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/history",
        json={"local_path": "/workspace/corrupted_repo"},
    )

    assert response.status_code == 500


def test_get_history_rejects_empty_path() -> None:
    response = client.post("/api/v1/repository/history", json={"local_path": ""})
    assert response.status_code == 422
