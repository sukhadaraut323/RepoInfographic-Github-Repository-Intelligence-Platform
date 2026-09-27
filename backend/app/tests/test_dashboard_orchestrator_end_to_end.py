"""
End-to-end test: ONE repository_url -> Orchestrator -> Modules 1-6 -> unified response.

Unlike `test_dashboard_endpoint.py` (which mocks `RepositoryOrchestratorService`
itself as a black box to test envelope/error formatting), this test wires a
REAL `RepositoryOrchestratorService` behind the endpoint's dependency
provider, with only its six leaf module services mocked. This proves the
actual internal chaining - not just that the endpoint formats a response -
while never making a real GitHub/network/filesystem call.

The HTTP request sent contains only `repository_url`, matching the
required user experience: no local_path, no branch, and no manual
per-module calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.dashboard import get_repository_orchestrator_service
from app.core.exceptions import RepositoryNotFoundError
from app.main import app
from app.services.repository_orchestrator_service import RepositoryOrchestratorService
from app.tests.analytics_factories import make_repository_metrics_result
from app.tests.test_repository_orchestrator_service import (
    make_analytics_dashboard_result,
    make_clone_result,
)
from app.tests.factories import make_git_history_result, make_repository_metadata, make_static_analysis_result

client = TestClient(app)

REPO_URL = "https://github.com/octo/demo"
LOCAL_PATH = "/workspace/octo_demo"


class WiredMocks:
    """A REAL RepositoryOrchestratorService wired with six mocked leaf services."""

    def __init__(self) -> None:
        self.call_order: list = []

        self.repository_service = MagicMock()

        async def metadata_side_effect(*_a, **_k):
            self.call_order.append("metadata")
            return make_repository_metadata()

        self.repository_service.analyze_repository = AsyncMock(side_effect=metadata_side_effect)

        self.cloner_service = MagicMock()

        def clone_side_effect(*_a, **_k):
            self.call_order.append("clone")
            return make_clone_result(local_path=LOCAL_PATH)

        self.cloner_service.clone_or_update_repository = MagicMock(side_effect=clone_side_effect)

        self.static_analysis_service = MagicMock()

        def static_side_effect(*_a, **_k):
            self.call_order.append("static_analysis")
            return make_static_analysis_result()

        self.static_analysis_service.analyze = MagicMock(side_effect=static_side_effect)

        self.git_history_service = MagicMock()

        def history_side_effect(*_a, **_k):
            self.call_order.append("git_history")
            return make_git_history_result()

        self.git_history_service.analyze = MagicMock(side_effect=history_side_effect)

        self.metrics_service = MagicMock()

        def metrics_side_effect(*_a, **_k):
            self.call_order.append("metrics")
            return make_repository_metrics_result()

        self.metrics_service.compute_metrics = MagicMock(side_effect=metrics_side_effect)

        self.analytics_service = MagicMock()

        def analytics_side_effect(*_a, **_k):
            self.call_order.append("analytics")
            return make_analytics_dashboard_result()

        self.analytics_service.build_dashboard = MagicMock(side_effect=analytics_side_effect)

    def build_real_orchestrator(self) -> RepositoryOrchestratorService:
        return RepositoryOrchestratorService(
            repository_service=self.repository_service,
            repository_cloner_service=self.cloner_service,
            static_analysis_service=self.static_analysis_service,
            git_history_service=self.git_history_service,
            repository_metrics_service=self.metrics_service,
            analytics_service=self.analytics_service,
        )


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_single_repository_url_triggers_the_complete_automatic_pipeline() -> None:
    """
    Sends only {"repository_url": ...} to POST /api/v1/dashboard/analyze
    and proves the entire Modules 1-6 chain executes automatically, in
    order, with every intermediate value passed forward without any
    manual input.
    """
    mocks = WiredMocks()
    app.dependency_overrides[get_repository_orchestrator_service] = mocks.build_real_orchestrator

    response = client.post(
        "/api/v1/dashboard/analyze",
        json={"repository_url": REPO_URL},  # <-- the ONLY input the user provides
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    # Every module ran, in the required dependency order.
    assert mocks.call_order == ["metadata", "clone", "static_analysis", "git_history", "metrics", "analytics"]

    # Module 2's generated local_path automatically reached Modules 3 and 4.
    mocks.static_analysis_service.analyze.assert_called_once_with(LOCAL_PATH)
    mocks.git_history_service.analyze.assert_called_once_with(LOCAL_PATH)

    # Modules 1, 3 and 4 automatically reached Module 5.
    mocks.metrics_service.compute_metrics.assert_called_once()
    _, metrics_kwargs = mocks.metrics_service.compute_metrics.call_args
    assert metrics_kwargs["repository_metadata"].full_name == "octo/demo"
    assert metrics_kwargs["static_analysis_result"].local_path is not None
    assert metrics_kwargs["git_history_result"].local_path is not None

    # Modules 1, 3, 4 and 5 automatically reached Module 6.
    mocks.analytics_service.build_dashboard.assert_called_once()
    _, analytics_kwargs = mocks.analytics_service.build_dashboard.call_args
    assert analytics_kwargs["repository_metadata"].full_name == "octo/demo"
    assert analytics_kwargs["repository_metrics_result"] is not None

    # The final Analytics result appears in the unified response returned to the user.
    assert body["data"]["analytics"]["health_gauge"]["value"] == 70.0

    # The request contained no local_path, no branch, and no per-module payloads.
    # (Only repository_url was ever sent above - this line documents that intent.)


def test_single_repository_url_pipeline_stops_cleanly_on_intermediate_failure() -> None:
    """A failure partway through still requires no user input beyond the original URL."""
    mocks = WiredMocks()
    mocks.repository_service.analyze_repository = AsyncMock(
        side_effect=RepositoryNotFoundError("Repository 'octo/demo' was not found on GitHub.")
    )
    app.dependency_overrides[get_repository_orchestrator_service] = mocks.build_real_orchestrator

    response = client.post("/api/v1/dashboard/analyze", json={"repository_url": REPO_URL})

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "REPOSITORY_NOT_FOUND"

    # The pipeline stopped immediately - no downstream module ran, and no
    # fabricated data was produced.
    mocks.cloner_service.clone_or_update_repository.assert_not_called()
    mocks.static_analysis_service.analyze.assert_not_called()
    mocks.git_history_service.analyze.assert_not_called()
    mocks.metrics_service.compute_metrics.assert_not_called()
    mocks.analytics_service.build_dashboard.assert_not_called()
