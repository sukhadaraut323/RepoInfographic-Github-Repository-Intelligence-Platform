"""Orchestrator + AI Layer integration and backward-compatibility tests."""

import json
from unittest.mock import ANY, AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.dashboard import get_repository_orchestrator_service
from app.clients.ollama_client import OllamaClient
from app.core.config import Settings
from app.core.exceptions import AIInvalidResponseError, OllamaUnavailableError
from app.main import app
from app.schemas.ai import AIInsightsResult, AIStatus
from app.services.ai_insights_service import AIInsightsService
from app.services.repository_orchestrator_service import RepositoryOrchestratorService
from app.tests.test_ai_insights_service import valid_ai_payload
from app.tests.test_repository_orchestrator_service import OrchestratorFixture, make_analytics_dashboard_result

URL = "https://github.com/octo/demo"


def orchestrator_with(fixture: OrchestratorFixture, ai_service) -> RepositoryOrchestratorService:
    return RepositoryOrchestratorService(
        repository_service=fixture.repository_service,
        repository_cloner_service=fixture.cloner_service,
        static_analysis_service=fixture.static_analysis_service,
        git_history_service=fixture.git_history_service,
        repository_metrics_service=fixture.metrics_service,
        analytics_service=fixture.analytics_service,
        ai_service=ai_service,
    )


def completed_result() -> AIInsightsResult:
    from datetime import datetime, timezone

    return AIInsightsResult(status=AIStatus.COMPLETED, model="m", generated_at=datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_ai_receives_all_five_module_outputs_after_analytics() -> None:
    f = OrchestratorFixture()
    ai = AsyncMock()
    ai.generate_insights.return_value = completed_result()

    result = await orchestrator_with(f, ai).analyze(URL)

    ai.generate_insights.assert_awaited_once_with(
        repository_metadata=f.repository_service.analyze_repository.return_value,
        static_analysis_result=f.static_analysis_service.analyze.return_value,
        git_history_result=f.git_history_service.analyze.return_value,
        repository_metrics_result=f.metrics_service.compute_metrics.return_value,
        analytics_result=f.analytics_service.build_dashboard.return_value,
        advanced_visualizations=ANY,
    )
    assert result.ai_insights.status == AIStatus.COMPLETED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,code",
    [(OllamaUnavailableError("Could not connect to Ollama."), "AI_SERVICE_UNAVAILABLE"), (AIInvalidResponseError("bad"), "AI_INVALID_RESPONSE")],
)
async def test_ai_failure_yields_partial_result_and_keeps_modules_1_to_6(error, code) -> None:
    f = OrchestratorFixture()
    ai = AsyncMock()
    ai.generate_insights.side_effect = error

    result = await orchestrator_with(f, ai).analyze(URL)

    assert result.ai_insights.status == AIStatus.UNAVAILABLE
    assert result.ai_insights.error.code == code and result.ai_insights.insights is None
    assert result.repository_metadata is not None and result.analytics is not None  # Modules 1-6 intact


@pytest.mark.asyncio
async def test_unexpected_ai_error_does_not_leak_details() -> None:
    f = OrchestratorFixture()
    ai = AsyncMock()
    ai.generate_insights.side_effect = RuntimeError("secret /internal/path token=abc")

    result = await orchestrator_with(f, ai).analyze(URL)

    assert result.ai_insights.error.code == "AI_ERROR"
    assert "secret" not in result.ai_insights.model_dump_json()


@pytest.mark.asyncio
async def test_ai_disabled_leaves_response_unchanged() -> None:
    result = await orchestrator_with(OrchestratorFixture(), None).analyze(URL)
    assert result.ai_insights is None


def test_endpoint_keeps_every_existing_field_and_adds_ai_insights() -> None:
    f = OrchestratorFixture()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": json.dumps(valid_ai_payload())}})

    settings = Settings(github_token="t", ollama_model="test-model")
    ai = AIInsightsService(OllamaClient(settings, transport=httpx.MockTransport(handler)))
    app.dependency_overrides[get_repository_orchestrator_service] = lambda: orchestrator_with(f, ai)
    try:
        response = TestClient(app).post("/api/v1/dashboard/analyze", json={"repository_url": URL})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    for field in ("repository_metadata", "clone_result", "static_analysis_result", "git_history_result",
                  "repository_metrics_result", "analytics", "generated_at"):
        assert field in data  # nothing removed
    assert data["ai_insights"]["status"] == "completed"
    assert data["ai_insights"]["insights"]["repository_summary"]["summary"] == "A summary."


def test_endpoint_returns_200_with_unavailable_ai_when_ollama_is_down() -> None:
    f = OrchestratorFixture()

    def handler(request):
        raise httpx.ConnectError("refused")

    ai = AIInsightsService(OllamaClient(Settings(github_token="t"), transport=httpx.MockTransport(handler)))
    app.dependency_overrides[get_repository_orchestrator_service] = lambda: orchestrator_with(f, ai)
    try:
        response = TestClient(app).post("/api/v1/dashboard/analyze", json={"repository_url": URL})
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200 and body["success"] is True
    assert body["data"]["ai_insights"]["status"] == "unavailable"
    assert body["data"]["ai_insights"]["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
    assert body["data"]["repository_metadata"] is not None
