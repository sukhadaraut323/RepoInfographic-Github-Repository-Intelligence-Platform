"""
REAL end-to-end integration test for the Repository Orchestrator.

Unlike `test_repository_orchestrator_service.py` (fully mocked, proves
call order/argument wiring) and `test_dashboard_orchestrator_end_to_end.py`
(proves the HTTP layer), this test proves the actual Modules 2-6 service
implementations execute correctly together against real data on disk:

    * A real local git repository is created (acting as the "remote" -
      git supports cloning from a local filesystem path, so no network
      access is required; this is the same technique already used by
      `test_git_client.py`).
    * The REAL `RepositoryClonerService` (backed by the REAL
      `GitRepositoryClient`/GitPython) clones it onto disk.
    * The REAL `StaticAnalysisService` scans the real cloned files.
    * The REAL `GitHistoryService` reads the real commit log.
    * The REAL `RepositoryMetricsService` and `AnalyticsService` compute
      from those real results.

Only the two genuine external-network boundaries are controlled, per the
correction prompt's "external network/GitHub dependencies may be
controlled appropriately":
    1. Module 1 (`RepositoryService.analyze_repository`) would otherwise
       call the real GitHub REST API - it is stubbed with a fixed,
       internally-consistent `RepositoryMetadata`.
    2. `RepositoryClonerService._normalize_clone_url` would otherwise
       normalize the URL into a real `https://github.com/...` clone
       target - it is patched to point at the local temp "remote"
       instead. Every other line of `RepositoryClonerService` runs
       unmodified (owner/repo parsing, workspace path resolution, status
       determination, real GitPython clone).

Nothing about Modules 1-6's own business logic is touched or mocked at
the method level for Modules 2-6.
"""

import logging
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from git import Repo

from app.api.v1.endpoints.analytics import get_analytics_service
from app.api.v1.endpoints.git_history import get_git_history_service
from app.api.v1.endpoints.metrics import get_repository_metrics_service
from app.api.v1.endpoints.static_analysis import get_static_analysis_service
from app.clients.git_client import GitRepositoryClient
from app.core.config import Settings
from app.schemas.clone_result import CloneStatus
from app.services.repository_cloner_service import RepositoryClonerService
from app.services.repository_orchestrator_service import RepositoryOrchestratorService
from app.tests.factories import make_repository_metadata

REPOSITORY_URL = "https://github.com/octo/demo-real"


def _build_source_repo(path: Path) -> Repo:
    """Create a real local git repository with two real commits."""
    repo = Repo.init(str(path), initial_branch="main")
    (path / "README.md").write_text("# Demo Repository\n\nA real repository for integration testing.\n")
    (path / "app.py").write_text("def main():\n    print('hello world')\n\n\nif __name__ == '__main__':\n    main()\n")
    repo.index.add(["README.md", "app.py"])
    repo.index.commit("Initial commit")

    (path / "utils.py").write_text("def add(a, b):\n    return a + b\n")
    repo.index.add(["utils.py"])
    repo.index.commit("Add utils module")

    return repo


def _build_real_orchestrator(tmp_path: Path, source_repo_path: Path) -> RepositoryOrchestratorService:
    """
    Wire a RepositoryOrchestratorService where only Module 1 (GitHub REST
    API) is stubbed. Modules 2-6 are real service instances.
    """
    # Module 1 stub - the only true GitHub REST API boundary. Owner/repo
    # match REPOSITORY_URL so parse_owner_repo() downstream stays consistent.
    repository_service = AsyncMock()
    repository_service.analyze_repository = AsyncMock(
        return_value=make_repository_metadata(full_name="octo/demo-real")
    )

    # Module 2 - real service, real GitPython client. Only the clone
    # *source* is redirected from a real GitHub URL to our local temp
    # "remote" repo, so no network access occurs.
    cloner_settings = Settings(github_token="test-token", workspace_directory=str(tmp_path / "workspace"))
    cloner_service = RepositoryClonerService(git_client=GitRepositoryClient(), settings=cloner_settings)
    cloner_service._normalize_clone_url = lambda _url: str(source_repo_path)  # noqa: SLF001

    # Modules 3-6 - real services, built via their own production
    # dependency providers (identical wiring to what the live app uses).
    return RepositoryOrchestratorService(
        repository_service=repository_service,
        repository_cloner_service=cloner_service,
        static_analysis_service=get_static_analysis_service(),
        git_history_service=get_git_history_service(),
        repository_metrics_service=get_repository_metrics_service(),
        analytics_service=get_analytics_service(),
    )


@pytest.mark.asyncio
async def test_real_pipeline_executes_all_modules_against_real_repository(tmp_path: Path, caplog) -> None:
    source_repo_path = tmp_path / "source_repo"
    source_repo_path.mkdir()
    _build_source_repo(source_repo_path)

    orchestrator = _build_real_orchestrator(tmp_path, source_repo_path)

    with caplog.at_level(logging.INFO, logger="app.services.repository_orchestrator_service"):
        result = await orchestrator.analyze(REPOSITORY_URL)

    # --- Module 2: a real clone genuinely happened on disk ---
    assert result.clone_result.status == CloneStatus.CLONED
    cloned_path = Path(result.clone_result.local_path)
    assert cloned_path.exists()
    assert (cloned_path / "README.md").exists()
    assert (cloned_path / "utils.py").exists()

    # --- Module 3: real static analysis scanned the real cloned files ---
    assert result.static_analysis_result.local_path == result.clone_result.local_path
    assert result.static_analysis_result.total_files >= 3  # README.md, app.py, utils.py
    assert result.static_analysis_result.total_lines > 0

    # --- Module 4: real git history read the real commit log ---
    assert result.git_history_result.local_path == result.clone_result.local_path
    assert result.git_history_result.total_commits == 2
    assert result.git_history_result.unique_contributors == 1

    # --- Modules 5 & 6: computed for real from the above real results ---
    assert result.repository_metrics_result is not None
    assert result.analytics is not None
    assert 0.0 <= result.analytics.health_gauge.value <= 100.0

    # --- Pipeline execution is visibly observable in the logs ---
    messages = [r.message for r in caplog.records]
    assert "[ORCHESTRATOR] Module 1: Metadata completed" in messages
    assert "[ORCHESTRATOR] Module 2: Clone completed" in messages
    assert "[ORCHESTRATOR] Module 3: Static analysis completed" in messages
    assert "[ORCHESTRATOR] Module 4: Git history completed" in messages
    assert "[ORCHESTRATOR] Module 5: Engineering metrics completed" in messages
    assert "[ORCHESTRATOR] Module 6: Analytics completed" in messages


@pytest.mark.asyncio
async def test_real_pipeline_logs_identify_the_failing_stage(tmp_path: Path, caplog) -> None:
    """When a real downstream module fails, the logs must name that stage."""
    source_repo_path = tmp_path / "source_repo"
    source_repo_path.mkdir()
    _build_source_repo(source_repo_path)

    orchestrator = _build_real_orchestrator(tmp_path, source_repo_path)

    # Force a real failure inside Module 3 by pointing static analysis at a
    # path that does not exist, simulating a genuine downstream fault
    # without touching any module's business logic.
    orchestrator._static_analysis_service.analyze = lambda _path: (_ for _ in ()).throw(
        RuntimeError("simulated static analysis failure")
    )

    with caplog.at_level(logging.INFO, logger="app.services.repository_orchestrator_service"):
        with pytest.raises(RuntimeError):
            await orchestrator.analyze(REPOSITORY_URL)

    messages = [r.message for r in caplog.records]
    assert "[ORCHESTRATOR] Module 2: Clone completed" in messages
    assert "[ORCHESTRATOR] Module 3: Static analysis failed" in messages
    assert "[ORCHESTRATOR] Module 4: Git history completed" not in messages
