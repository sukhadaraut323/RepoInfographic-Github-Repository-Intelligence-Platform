"""Integration tests for POST /api/v1/repository/metrics."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.metrics import get_repository_metrics_service
from app.main import app
from app.schemas.metrics import RepositoryMetricsResult, SubScore
from app.tests.factories import make_git_history_result, make_repository_metadata, make_static_analysis_result

client = TestClient(app)

SAMPLE_SUBSCORE = SubScore(score=75.0, evidence=["evidence item"], reasons=["reason item"])
SAMPLE_RESULT = RepositoryMetricsResult(
    documentation_score=SAMPLE_SUBSCORE,
    codebase_score=SAMPLE_SUBSCORE,
    activity_score=SAMPLE_SUBSCORE,
    community_score=SAMPLE_SUBSCORE,
    maintainability_score=SAMPLE_SUBSCORE,
    best_practices_score=SAMPLE_SUBSCORE,
    overall_health_score=SAMPLE_SUBSCORE,
    calculated_at=datetime.now(timezone.utc),
)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def _build_request_payload() -> dict:
    metadata = make_repository_metadata()
    static_result = make_static_analysis_result()
    history_result = make_git_history_result()
    return json.loads(
        json.dumps(
            {
                "repository_metadata": metadata.model_dump(mode="json"),
                "static_analysis_result": static_result.model_dump(mode="json"),
                "git_history_result": history_result.model_dump(mode="json"),
            }
        )
    )


def test_get_metrics_success() -> None:
    mock_service = MagicMock()
    mock_service.compute_metrics.return_value = SAMPLE_RESULT
    app.dependency_overrides[get_repository_metrics_service] = lambda: mock_service

    response = client.post("/api/v1/repository/metrics", json=_build_request_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["documentation_score"]["score"] == 75.0
    assert body["overall_health_score"]["reasons"] == ["reason item"]
    mock_service.compute_metrics.assert_called_once()


def test_get_metrics_rejects_missing_fields() -> None:
    response = client.post("/api/v1/repository/metrics", json={"repository_metadata": {}})
    assert response.status_code == 422


def test_get_metrics_real_pipeline_end_to_end() -> None:
    """No dependency override: exercises the real service through the real endpoint."""
    response = client.post("/api/v1/repository/metrics", json=_build_request_payload())

    assert response.status_code == 200
    body = response.json()
    for key in [
        "documentation_score",
        "codebase_score",
        "activity_score",
        "community_score",
        "maintainability_score",
        "best_practices_score",
        "overall_health_score",
    ]:
        assert 0 <= body[key]["score"] <= 100
        assert isinstance(body[key]["evidence"], list)
        assert isinstance(body[key]["reasons"], list)
