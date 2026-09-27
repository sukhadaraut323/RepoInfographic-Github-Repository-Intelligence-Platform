"""Integration tests for POST /api/v1/repository/analytics."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.analytics import get_analytics_service
from app.main import app
from app.schemas.analytics import AnalyticsDashboardResult, HealthGauge
from app.tests.analytics_factories import make_repository_metrics_result
from app.tests.factories import make_git_history_result, make_repository_metadata, make_static_analysis_result

client = TestClient(app)

SAMPLE_RESULT = AnalyticsDashboardResult(
    language_distribution=[],
    commit_timeline=[],
    overview_cards=[],
    health_gauge=HealthGauge(value=80.0, min=0, max=100, label="Repository Health Score", status="Good"),
    score_breakdown=[],
    repository_timeline=[],
    file_type_distribution=[],
    largest_directories=[],
    generated_at=datetime.now(timezone.utc),
)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def _build_request_payload() -> dict:
    metadata = make_repository_metadata()
    static_result = make_static_analysis_result()
    history_result = make_git_history_result()
    metrics_result = make_repository_metrics_result()
    return json.loads(
        json.dumps(
            {
                "repository_metadata": metadata.model_dump(mode="json"),
                "static_analysis_result": static_result.model_dump(mode="json"),
                "git_history_result": history_result.model_dump(mode="json"),
                "repository_metrics_result": metrics_result.model_dump(mode="json"),
            }
        )
    )


def test_get_analytics_success() -> None:
    mock_service = MagicMock()
    mock_service.build_dashboard.return_value = SAMPLE_RESULT
    app.dependency_overrides[get_analytics_service] = lambda: mock_service

    response = client.post("/api/v1/repository/analytics", json=_build_request_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["health_gauge"]["status"] == "Good"
    mock_service.build_dashboard.assert_called_once()


def test_get_analytics_rejects_missing_fields() -> None:
    response = client.post("/api/v1/repository/analytics", json={"repository_metadata": {}})
    assert response.status_code == 422


def test_get_analytics_real_pipeline_end_to_end() -> None:
    """No dependency override: exercises the real service through the real endpoint."""
    response = client.post("/api/v1/repository/analytics", json=_build_request_payload())

    assert response.status_code == 200
    body = response.json()
    for key in [
        "language_distribution",
        "commit_timeline",
        "overview_cards",
        "health_gauge",
        "score_breakdown",
        "repository_timeline",
        "file_type_distribution",
        "largest_directories",
        "generated_at",
    ]:
        assert key in body
    assert len(body["overview_cards"]) == 9
    assert len(body["score_breakdown"]) == 6
