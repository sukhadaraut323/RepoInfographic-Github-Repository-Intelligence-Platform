"""Unit tests for RepositoryOrchestratorService (Repository Orchestrator, Phase 1)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import (
    GitHistoryAnalysisError,
    InvalidRepositoryURLError,
    RepositoryCloneError,
    RepositoryNotFoundError,
    StaticAnalysisError,
)
from app.schemas.analytics import AnalyticsDashboardResult, HealthGauge
from app.schemas.clone_result import CloneStatus, RepositoryCloneResult
from app.services.repository_orchestrator_service import RepositoryOrchestratorService
from app.tests.analytics_factories import make_repository_metrics_result
from app.tests.factories import make_git_history_result, make_repository_metadata, make_static_analysis_result

REPO_URL = "https://github.com/octo/demo"
LOCAL_PATH = "/workspace/octo_demo"


def make_analytics_dashboard_result() -> AnalyticsDashboardResult:
    from datetime import datetime, timezone

    return AnalyticsDashboardResult(
        health_gauge=HealthGauge(value=70.0, status="Good"),
        generated_at=datetime.now(timezone.utc),
    )


def make_clone_result(local_path: str = LOCAL_PATH) -> RepositoryCloneResult:
    from datetime import datetime, timezone

    return RepositoryCloneResult(
        owner="octo",
        repository="demo",
        branch="main",
        local_path=local_path,
        status=CloneStatus.CLONED,
        last_updated=datetime.now(timezone.utc),
    )


class OrchestratorFixture:
    """Bundles a RepositoryOrchestratorService with its six mocked dependencies."""

    def __init__(self) -> None:
        self.repository_service = MagicMock()
        self.repository_service.analyze_repository = AsyncMock(return_value=make_repository_metadata())

        self.cloner_service = MagicMock()
        self.cloner_service.clone_or_update_repository = MagicMock(return_value=make_clone_result())

        self.static_analysis_service = MagicMock()
        self.static_analysis_service.analyze = MagicMock(return_value=make_static_analysis_result())

        self.git_history_service = MagicMock()
        self.git_history_service.analyze = MagicMock(return_value=make_git_history_result())

        self.metrics_service = MagicMock()
        self.metrics_service.compute_metrics = MagicMock(return_value=make_repository_metrics_result())

        self.analytics_service = MagicMock()
        self.analytics_service.build_dashboard = MagicMock(return_value=make_analytics_dashboard_result())

        self.orchestrator = RepositoryOrchestratorService(
            repository_service=self.repository_service,
            repository_cloner_service=self.cloner_service,
            static_analysis_service=self.static_analysis_service,
            git_history_service=self.git_history_service,
            repository_metrics_service=self.metrics_service,
            analytics_service=self.analytics_service,
        )


@pytest.fixture()
def fixture() -> OrchestratorFixture:
    return OrchestratorFixture()


@pytest.mark.asyncio
async def test_successful_complete_pipeline(fixture: OrchestratorFixture) -> None:
    result = await fixture.orchestrator.analyze(REPO_URL)

    assert result.repository_metadata == fixture.repository_service.analyze_repository.return_value
    assert result.clone_result == fixture.cloner_service.clone_or_update_repository.return_value
    assert result.static_analysis_result == fixture.static_analysis_service.analyze.return_value
    assert result.git_history_result == fixture.git_history_service.analyze.return_value
    assert result.repository_metrics_result == fixture.metrics_service.compute_metrics.return_value
    assert result.analytics == fixture.analytics_service.build_dashboard.return_value
    assert result.generated_at is not None


@pytest.mark.asyncio
async def test_correct_service_call_order_and_arguments(fixture: OrchestratorFixture) -> None:
    """
    Proves the required automatic data flow end-to-end at the service layer:
    a single `repository_url` in, with every intermediate value (metadata,
    local_path, static analysis result, git history result, metrics result)
    passed forward automatically - no manual/intermediate input required.
    """
    call_order = []
    produced = {}  # captures each stage's actual returned object, by name

    async def metadata_side_effect(*_a, **_k):
        call_order.append("metadata")
        produced["metadata"] = make_repository_metadata()
        return produced["metadata"]

    fixture.repository_service.analyze_repository = AsyncMock(side_effect=metadata_side_effect)

    def clone_side_effect(*_a, **_k):
        call_order.append("clone")
        produced["clone"] = make_clone_result()
        return produced["clone"]

    fixture.cloner_service.clone_or_update_repository.side_effect = clone_side_effect

    def static_side_effect(*_a, **_k):
        call_order.append("static_analysis")
        produced["static"] = make_static_analysis_result()
        return produced["static"]

    fixture.static_analysis_service.analyze.side_effect = static_side_effect

    def history_side_effect(*_a, **_k):
        call_order.append("git_history")
        produced["history"] = make_git_history_result()
        return produced["history"]

    fixture.git_history_service.analyze.side_effect = history_side_effect

    def metrics_side_effect(*_a, **_k):
        call_order.append("metrics")
        produced["metrics"] = make_repository_metrics_result()
        return produced["metrics"]

    fixture.metrics_service.compute_metrics.side_effect = metrics_side_effect

    def analytics_side_effect(*_a, **_k):
        call_order.append("analytics")
        produced["analytics"] = make_analytics_dashboard_result()
        return produced["analytics"]

    fixture.analytics_service.build_dashboard.side_effect = analytics_side_effect

    result = await fixture.orchestrator.analyze(REPO_URL)

    # 1. Dependency order is respected.
    assert call_order == ["metadata", "clone", "static_analysis", "git_history", "metrics", "analytics"]

    # 2. Clone's generated local_path automatically reaches Static Analysis and Git History
    #    - the user never supplies it.
    fixture.static_analysis_service.analyze.assert_called_once_with(produced["clone"].local_path)
    fixture.git_history_service.analyze.assert_called_once_with(produced["clone"].local_path)

    # 3. Metadata, Static Analysis and Git History outputs automatically reach Metrics.
    fixture.metrics_service.compute_metrics.assert_called_once_with(
        repository_metadata=produced["metadata"],
        static_analysis_result=produced["static"],
        git_history_result=produced["history"],
    )

    # 4. Metadata, Static Analysis, Git History and Metrics outputs automatically reach Analytics.
    fixture.analytics_service.build_dashboard.assert_called_once_with(
        repository_metadata=produced["metadata"],
        static_analysis_result=produced["static"],
        git_history_result=produced["history"],
        repository_metrics_result=produced["metrics"],
    )

    # 5. The final Analytics result appears, unmodified, in the unified response.
    assert result.analytics is produced["analytics"]
    assert result.repository_metrics_result is produced["metrics"]


@pytest.mark.asyncio
async def test_invalid_repository_url_propagates(fixture: OrchestratorFixture) -> None:
    fixture.repository_service.analyze_repository = AsyncMock(
        side_effect=InvalidRepositoryURLError("URL could not be parsed.")
    )

    with pytest.raises(InvalidRepositoryURLError):
        await fixture.orchestrator.analyze("not-a-valid-url")

    fixture.cloner_service.clone_or_update_repository.assert_not_called()


@pytest.mark.asyncio
async def test_metadata_failure_propagates_and_stops_pipeline(fixture: OrchestratorFixture) -> None:
    fixture.repository_service.analyze_repository = AsyncMock(
        side_effect=RepositoryNotFoundError("Repository 'octo/missing' was not found on GitHub.")
    )

    with pytest.raises(RepositoryNotFoundError):
        await fixture.orchestrator.analyze(REPO_URL)

    fixture.cloner_service.clone_or_update_repository.assert_not_called()
    fixture.static_analysis_service.analyze.assert_not_called()
    fixture.git_history_service.analyze.assert_not_called()
    fixture.metrics_service.compute_metrics.assert_not_called()
    fixture.analytics_service.build_dashboard.assert_not_called()


@pytest.mark.asyncio
async def test_clone_failure_propagates_and_stops_pipeline(fixture: OrchestratorFixture) -> None:
    fixture.cloner_service.clone_or_update_repository.side_effect = RepositoryCloneError("git clone failed.")

    with pytest.raises(RepositoryCloneError):
        await fixture.orchestrator.analyze(REPO_URL)

    fixture.static_analysis_service.analyze.assert_not_called()
    fixture.git_history_service.analyze.assert_not_called()
    fixture.metrics_service.compute_metrics.assert_not_called()
    fixture.analytics_service.build_dashboard.assert_not_called()


@pytest.mark.asyncio
async def test_static_analysis_failure_propagates_and_stops_pipeline(fixture: OrchestratorFixture) -> None:
    fixture.static_analysis_service.analyze.side_effect = StaticAnalysisError("scan failed.")

    with pytest.raises(StaticAnalysisError):
        await fixture.orchestrator.analyze(REPO_URL)

    fixture.git_history_service.analyze.assert_not_called()
    fixture.metrics_service.compute_metrics.assert_not_called()
    fixture.analytics_service.build_dashboard.assert_not_called()


@pytest.mark.asyncio
async def test_git_history_failure_propagates_and_stops_pipeline(fixture: OrchestratorFixture) -> None:
    fixture.git_history_service.analyze.side_effect = GitHistoryAnalysisError("history read failed.")

    with pytest.raises(GitHistoryAnalysisError):
        await fixture.orchestrator.analyze(REPO_URL)

    fixture.metrics_service.compute_metrics.assert_not_called()
    fixture.analytics_service.build_dashboard.assert_not_called()


@pytest.mark.asyncio
async def test_metrics_failure_propagates_and_stops_pipeline(fixture: OrchestratorFixture) -> None:
    fixture.metrics_service.compute_metrics.side_effect = RuntimeError("unexpected metrics failure.")

    with pytest.raises(RuntimeError):
        await fixture.orchestrator.analyze(REPO_URL)

    fixture.analytics_service.build_dashboard.assert_not_called()


@pytest.mark.asyncio
async def test_analytics_failure_propagates(fixture: OrchestratorFixture) -> None:
    fixture.analytics_service.build_dashboard.side_effect = RuntimeError("unexpected analytics failure.")

    with pytest.raises(RuntimeError):
        await fixture.orchestrator.analyze(REPO_URL)
