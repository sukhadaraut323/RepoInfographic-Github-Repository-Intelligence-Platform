"""Integration tests for POST /api/v1/repository/analyze."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.repository import get_repository_service
from app.core.exceptions import RepositoryNotFoundError
from app.main import app
from app.schemas.repository import RepositoryMetadata, RepositoryOwner

client = TestClient(app)

SAMPLE_METADATA = RepositoryMetadata(
    full_name="fastapi/fastapi",
    owner=RepositoryOwner(login="fastapi", type="Organization", avatar_url=None),
    description="FastAPI framework.",
    html_url="https://github.com/fastapi/fastapi",
    default_branch="master",
    visibility="public",
    is_archived=False,
    is_fork=False,
    stargazers_count=70000,
    forks_count=6000,
    watchers_count=70000,
    open_issues_count=120,
    size_kb=15000,
    license_name="MIT License",
    topics=["python", "api"],
    primary_language="Python",
    languages={"Python": 900000, "JavaScript": 5000},
    created_at="2018-12-08T00:00:00Z",
    updated_at="2024-01-01T00:00:00Z",
    pushed_at="2024-01-02T00:00:00Z",
)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_analyze_repository_success() -> None:
    mock_service = AsyncMock()
    mock_service.analyze_repository.return_value = SAMPLE_METADATA
    app.dependency_overrides[get_repository_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/analyze",
        json={"repository_url": "https://github.com/fastapi/fastapi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "fastapi/fastapi"
    assert body["primary_language"] == "Python"
    assert body["languages"]["Python"] == 900000


def test_analyze_repository_not_found() -> None:
    mock_service = AsyncMock()
    mock_service.analyze_repository.side_effect = RepositoryNotFoundError(
        "Repository 'owner/missing' was not found on GitHub."
    )
    app.dependency_overrides[get_repository_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/analyze",
        json={"repository_url": "https://github.com/owner/missing"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_analyze_repository_rejects_empty_url() -> None:
    response = client.post("/api/v1/repository/analyze", json={"repository_url": ""})
    assert response.status_code == 422  # Pydantic validation error (min_length=1)
