"""Integration tests for POST /api/v1/dashboard/analyze (Repository Orchestrator)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.dashboard import get_repository_orchestrator_service
from app.core.exceptions import (
    GitHistoryAnalysisError,
    InvalidRepositoryURLError,
    RepositoryCloneError,
    RepositoryNotFoundError,
    StaticAnalysisError,
)
from app.main import app
from app.schemas.clone_result import CloneStatus, RepositoryCloneResult
from app.schemas.dashboard import DashboardData
from app.tests.analytics_factories import make_repository_metrics_result
from app.tests.factories import make_git_history_result, make_repository_metadata, make_static_analysis_result

client = TestClient(app)


def make_dashboard_data() -> DashboardData:
    from app.schemas.analytics import AnalyticsDashboardResult, HealthGauge

    return DashboardData(
        repository_metadata=make_repository_metadata(),
        clone_result=RepositoryCloneResult(
            owner="octo",
            repository="demo",
            branch="main",
            local_path="/workspace/octo_demo",
            status=CloneStatus.CLONED,
            last_updated=datetime.now(timezone.utc),
        ),
        static_analysis_result=make_static_analysis_result(),
        git_history_result=make_git_history_result(),
        repository_metrics_result=make_repository_metrics_result(),
        analytics=AnalyticsDashboardResult(
            health_gauge=HealthGauge(value=70.0, status="Good"),
            generated_at=datetime.now(timezone.utc),
        ),
        generated_at=datetime.now(timezone.utc),
    )


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_dashboard_analyze_success_returns_unified_envelope() -> None:
    mock_service = AsyncMock()
    mock_service.analyze.return_value = make_dashboard_data()
    app.dependency_overrides[get_repository_orchestrator_service] = lambda: mock_service

    response = client.post(
        "/api/v1/dashboard/analyze",
        json={"repository_url": "https://github.com/octo/demo"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["repository_metadata"]["full_name"] == "octo/demo"
    assert body["data"]["clone_result"]["status"] == "cloned"
    assert body["data"]["analytics"]["health_gauge"]["value"] == 70.0
    mock_service.analyze.assert_awaited_once_with("https://github.com/octo/demo")


@pytest.mark.parametrize(
    "exception,expected_status,expected_code",
    [
        (InvalidRepositoryURLError("bad url"), 400, "INVALID_REPOSITORY_URL"),
        (RepositoryNotFoundError("not found"), 404, "REPOSITORY_NOT_FOUND"),
        (RepositoryCloneError("clone failed"), 502, "REPOSITORY_CLONE_ERROR"),
        (StaticAnalysisError("scan failed"), 500, "STATIC_ANALYSIS_ERROR"),
        (GitHistoryAnalysisError("history failed"), 500, "GIT_HISTORY_ANALYSIS_ERROR"),
    ],
)
def test_dashboard_analyze_returns_structured_error_envelope(exception, expected_status, expected_code) -> None:
    mock_service = AsyncMock()
    mock_service.analyze.side_effect = exception
    app.dependency_overrides[get_repository_orchestrator_service] = lambda: mock_service

    response = client.post(
        "/api/v1/dashboard/analyze",
        json={"repository_url": "https://github.com/octo/demo"},
    )

    assert response.status_code == expected_status
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == expected_code
    assert "error" in body and "data" not in body


def test_dashboard_analyze_unexpected_error_returns_generic_500_without_internals() -> None:
    mock_service = AsyncMock()
    mock_service.analyze.side_effect = RuntimeError("some secret internal detail")
    app.dependency_overrides[get_repository_orchestrator_service] = lambda: mock_service

    response = client.post(
        "/api/v1/dashboard/analyze",
        json={"repository_url": "https://github.com/octo/demo"},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "secret internal detail" not in response.text


def test_dashboard_analyze_rejects_empty_url() -> None:
    response = client.post("/api/v1/dashboard/analyze", json={"repository_url": ""})
    assert response.status_code == 422  # Pydantic validation error (min_length=1)


def test_existing_module_endpoints_remain_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/repository/analyze" in paths
    assert "/api/v1/repository/clone" in paths
    assert "/api/v1/repository/scan" in paths
    assert "/api/v1/repository/history" in paths
    assert "/api/v1/repository/metrics" in paths
    assert "/api/v1/repository/analytics" in paths
    assert "/api/v1/dashboard/analyze" in paths
