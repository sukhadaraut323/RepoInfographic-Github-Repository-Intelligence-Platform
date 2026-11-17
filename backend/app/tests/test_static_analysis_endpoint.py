"""Integration tests for POST /api/v1/repository/scan."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.static_analysis import get_static_analysis_service
from app.core.exceptions import RepositoryPathNotFoundError, StaticAnalysisError
from app.main import app
from app.schemas.static_analysis import DirectoryTreeNode, RepositoryMarkerFiles, RootMarkerFile, StaticAnalysisResult

client = TestClient(app)

SAMPLE_RESULT = StaticAnalysisResult(
    local_path="/workspace/fastapi_fastapi",
    total_files=10,
    total_directories=3,
    supported_source_files=8,
    language_distribution=[],
    total_lines=500,
    blank_lines=50,
    comment_lines=40,
    project_types=["Python (pip)"],
    directory_tree=DirectoryTreeNode(name="fastapi_fastapi", type="directory", children=[]),
    marker_files=RepositoryMarkerFiles(
        readme=RootMarkerFile(present=True, path="README.md"), license=RootMarkerFile(present=False),
        contributing=RootMarkerFile(present=False), changelog=RootMarkerFile(present=False),
        dockerfile=RootMarkerFile(present=False), docker_compose=RootMarkerFile(present=False),
        gitignore=RootMarkerFile(present=True, path=".gitignore"), editorconfig=RootMarkerFile(present=False),
        env_example=RootMarkerFile(present=False), precommit_config=RootMarkerFile(present=False),
        has_ci_config=True, has_docs_directory=True, has_api_docs_tooling=False,
    ),
    readme_content="# FastAPI\n",
    ignored_directories=[".git", "node_modules"],
    scanned_at=datetime.now(timezone.utc),
)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_scan_repository_success() -> None:
    mock_service = MagicMock()
    mock_service.analyze.return_value = SAMPLE_RESULT
    app.dependency_overrides[get_static_analysis_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/scan",
        json={"local_path": "/workspace/fastapi_fastapi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_files"] == 10
    assert body["supported_source_files"] == 8
    assert body["project_types"] == ["Python (pip)"]
    mock_service.analyze.assert_called_once_with("/workspace/fastapi_fastapi")


def test_scan_repository_path_not_found_returns_404() -> None:
    mock_service = MagicMock()
    mock_service.analyze.side_effect = RepositoryPathNotFoundError(
        "Local repository path '/workspace/missing' does not exist."
    )
    app.dependency_overrides[get_static_analysis_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/scan",
        json={"local_path": "/workspace/missing"},
    )

    assert response.status_code == 404


def test_scan_repository_internal_error_returns_500() -> None:
    mock_service = MagicMock()
    mock_service.analyze.side_effect = StaticAnalysisError("Unexpected failure while scanning.")
    app.dependency_overrides[get_static_analysis_service] = lambda: mock_service

    response = client.post(
        "/api/v1/repository/scan",
        json={"local_path": "/workspace/fastapi_fastapi"},
    )

    assert response.status_code == 500


def test_scan_repository_rejects_empty_path() -> None:
    response = client.post("/api/v1/repository/scan", json={"local_path": ""})
    assert response.status_code == 422
