"""Unit tests for app.services.repository_service.RepositoryService."""

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import RepositoryNotFoundError
from app.services.repository_service import RepositoryService

SAMPLE_REPO_RESPONSE = {
    "full_name": "fastapi/fastapi",
    "owner": {"login": "fastapi", "type": "Organization", "avatar_url": "https://avatars.githubusercontent.com/u/1"},
    "description": "FastAPI framework, high performance, easy to learn.",
    "html_url": "https://github.com/fastapi/fastapi",
    "default_branch": "master",
    "visibility": "public",
    "archived": False,
    "fork": False,
    "stargazers_count": 70000,
    "forks_count": 6000,
    "watchers_count": 70000,
    "open_issues_count": 120,
    "size": 15000,
    "license": {"name": "MIT License"},
    "topics": ["python", "api", "async"],
    "language": "Python",
    "created_at": "2018-12-08T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "pushed_at": "2024-01-02T00:00:00Z",
}

SAMPLE_LANGUAGES_RESPONSE = {"Python": 900000, "JavaScript": 5000}


@pytest.mark.asyncio
async def test_analyze_repository_maps_metadata_correctly() -> None:
    mock_client = AsyncMock()
    mock_client.get_repository.return_value = SAMPLE_REPO_RESPONSE
    mock_client.get_repository_languages.return_value = SAMPLE_LANGUAGES_RESPONSE

    service = RepositoryService(github_client=mock_client)
    result = await service.analyze_repository("https://github.com/fastapi/fastapi")

    assert result.full_name == "fastapi/fastapi"
    assert result.owner.login == "fastapi"
    assert result.stargazers_count == 70000
    assert result.license_name == "MIT License"
    assert result.primary_language == "Python"  # highest byte count
    assert result.languages == SAMPLE_LANGUAGES_RESPONSE
    mock_client.get_repository.assert_awaited_once_with("fastapi", "fastapi")
    mock_client.get_repository_languages.assert_awaited_once_with("fastapi", "fastapi")


@pytest.mark.asyncio
async def test_analyze_repository_propagates_not_found() -> None:
    mock_client = AsyncMock()
    mock_client.get_repository.side_effect = RepositoryNotFoundError("not found")

    service = RepositoryService(github_client=mock_client)

    with pytest.raises(RepositoryNotFoundError):
        await service.analyze_repository("https://github.com/owner/does-not-exist")
