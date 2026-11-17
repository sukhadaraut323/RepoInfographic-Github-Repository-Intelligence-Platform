"""
Repository Orchestrator - single backend entry point for the dashboard.

Coordinates Modules 1-6 in their required dependency order, using direct
Python service calls only (no internal HTTP requests, per the Engineering
Constitution and API Contracts). This service duplicates none of the
underlying modules' business logic - it only sequences existing service
calls and assembles their already-structured outputs into one unified
`DashboardData` payload.

Pipeline:
    Repository URL
        -> Metadata (Module 1)
        -> Clone (Module 2)
        -> Static Analysis (Module 3, uses clone's local_path)
        -> Git History (Module 4, uses clone's local_path)
        -> Engineering Metrics (Module 5, uses Modules 1/3/4 outputs)
        -> Analytics (Module 6, uses Modules 1/3/4/5 outputs)
        -> Unified DashboardData

Any exception raised by an underlying module (see `app.core.exceptions`)
propagates unchanged - this service performs no error translation itself.
Mapping exceptions to HTTP responses is the API layer's responsibility.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.core.exceptions import AIServiceError, OllamaUnavailableError, AIInvalidResponseError
from app.schemas.ai import AIErrorDetail, AIInsightsResult, AIStatus
from app.schemas.dashboard import DashboardData
from app.services.ai_insights_service import AIInsightsService
from app.services.analytics_service import AnalyticsService
from app.services.git_history_service import GitHistoryService
from app.services.repository_cloner_service import RepositoryClonerService
from app.services.repository_metrics_service import RepositoryMetricsService
from app.services.repository_service import RepositoryService
from app.services.static_analysis_service import StaticAnalysisService
from app.services.advanced_visualization_service import AdvancedVisualizationService

logger = logging.getLogger(__name__)


class RepositoryOrchestratorService:
    """Coordinates Modules 1-6 into one complete repository analysis pipeline."""

    def __init__(
        self,
        repository_service: RepositoryService,
        repository_cloner_service: RepositoryClonerService,
        static_analysis_service: StaticAnalysisService,
        git_history_service: GitHistoryService,
        repository_metrics_service: RepositoryMetricsService,
        analytics_service: AnalyticsService,
        ai_service: Optional[AIInsightsService] = None,
        visualization_service: Optional[AdvancedVisualizationService] = None,
    ) -> None:
        self._repository_service = repository_service
        self._repository_cloner_service = repository_cloner_service
        self._static_analysis_service = static_analysis_service
        self._git_history_service = git_history_service
        self._repository_metrics_service = repository_metrics_service
        self._analytics_service = analytics_service
        self._ai_service = ai_service  # optional: None disables the AI Layer
        self._visualization_service = visualization_service or AdvancedVisualizationService()

    async def analyze(self, repository_url: str, branch: Optional[str] = None) -> DashboardData:
        """
        Run the complete Modules 1-6 pipeline for a single repository URL.

        Args:
            repository_url: Public GitHub repository URL.
            branch: Optional branch to check out (Module 2). Defaults to
                the repository's default branch when omitted.

        Returns:
            A populated `DashboardData` combining every module's output.

        Raises:
            Any exception defined in `app.core.exceptions` that a
            downstream module raises (e.g. InvalidRepositoryURLError,
            RepositoryNotFoundError, RepositoryCloneError,
            RepositoryPathNotFoundError, StaticAnalysisError,
            GitHistoryAnalysisError, etc.). See individual module
            services for the full list.
        """
        logger.info("[ORCHESTRATOR] Starting repository analysis for %s", repository_url)
        pipeline_started = time.monotonic()

        # Module 1 - already async, awaited directly.
        stage_started = time.monotonic()
        try:
            repository_metadata = await self._repository_service.analyze_repository(repository_url)
        except Exception:
            logger.error("[ORCHESTRATOR] Module 1: Metadata failed")
            raise
        logger.info("[ORCHESTRATOR] Module 1: Metadata completed")
        logger.info("[PERFORMANCE] Metadata: %.2fs", time.monotonic() - stage_started)

        # Modules 2-4 perform blocking filesystem/git I/O. Running them via
        # `asyncio.to_thread` keeps this coroutine's blocking work off the
        # event loop without introducing internal HTTP calls or forcing an
        # unnecessary async rewrite of the underlying (correctly synchronous)
        # service methods themselves.
        stage_started = time.monotonic()
        try:
            clone_result = await asyncio.to_thread(
                self._repository_cloner_service.clone_or_update_repository,
                repository_url,
                branch,
            )
        except Exception:
            logger.error("[ORCHESTRATOR] Module 2: Clone failed")
            raise
        logger.info("[ORCHESTRATOR] Module 2: Clone completed")
        logger.info("[PERFORMANCE] Clone: %.2fs", time.monotonic() - stage_started)

        stage_started = time.monotonic()
        try:
            static_analysis_result = await asyncio.to_thread(
                self._static_analysis_service.analyze,
                clone_result.local_path,
            )
        except Exception:
            logger.error("[ORCHESTRATOR] Module 3: Static analysis failed")
            raise
        logger.info("[ORCHESTRATOR] Module 3: Static analysis completed")
        logger.info("[PERFORMANCE] Static Analysis: %.2fs", time.monotonic() - stage_started)

        stage_started = time.monotonic()
        try:
            git_history_result = await asyncio.to_thread(
                self._git_history_service.analyze,
                clone_result.local_path,
            )
        except Exception:
            logger.error("[ORCHESTRATOR] Module 4: Git history failed")
            raise
        logger.info("[ORCHESTRATOR] Module 4: Git history completed")
        logger.info("[PERFORMANCE] Git History: %.2fs", time.monotonic() - stage_started)

        # Modules 5-6 are pure in-memory computation over already-collected
        # data (no I/O), so - consistent with their own FastAPI wrappers -
        # they are called directly rather than offloaded to a thread.
        stage_started = time.monotonic()
        try:
            repository_metrics_result = self._repository_metrics_service.compute_metrics(
                repository_metadata=repository_metadata,
                static_analysis_result=static_analysis_result,
                git_history_result=git_history_result,
            )
        except Exception:
            logger.error("[ORCHESTRATOR] Module 5: Engineering metrics failed")
            raise
        logger.info("[ORCHESTRATOR] Module 5: Engineering metrics completed")
        logger.info("[PERFORMANCE] Engineering Metrics: %.2fs", time.monotonic() - stage_started)

        stage_started = time.monotonic()
        try:
            analytics_result = self._analytics_service.build_dashboard(
                repository_metadata=repository_metadata,
                static_analysis_result=static_analysis_result,
                git_history_result=git_history_result,
                repository_metrics_result=repository_metrics_result,
            )
        except Exception:
            logger.error("[ORCHESTRATOR] Module 6: Analytics failed")
            raise
        logger.info("[ORCHESTRATOR] Module 6: Analytics completed")
        logger.info("[PERFORMANCE] Analytics: %.2fs", time.monotonic() - stage_started)

        advanced_visualizations = None
        logger.info('[ORCHESTRATOR] Advanced Visualizations: started')
        stage_started = time.monotonic()
        try:
            advanced_visualizations = await asyncio.to_thread(
                self._visualization_service.analyze, clone_result.local_path
            )
            logger.info("[ORCHESTRATOR] Advanced visualizations completed")
        except Exception:
            logger.exception("[ORCHESTRATOR] Advanced visualization extraction failed; continuing without it")
        logger.info("[PERFORMANCE] Advanced Visualizations: %.2fs", time.monotonic() - stage_started)

        stage_started = time.monotonic()
        ai_insights = await self._run_ai_layer(
            repository_metadata, static_analysis_result, git_history_result, repository_metrics_result, analytics_result,
            advanced_visualizations,
        )
        logger.info("[PERFORMANCE] Ollama AI Generation: %.2fs", time.monotonic() - stage_started)

        logger.info("[ORCHESTRATOR] Repository analysis completed for %s", repository_url)
        logger.info("[PERFORMANCE] Total: %.2fs", time.monotonic() - pipeline_started)

        return DashboardData(
            repository_metadata=repository_metadata,
            clone_result=clone_result,
            static_analysis_result=static_analysis_result,
            git_history_result=git_history_result,
            repository_metrics_result=repository_metrics_result,
            analytics=analytics_result,
            generated_at=datetime.now(timezone.utc),
            ai_insights=ai_insights,
            advanced_visualizations=advanced_visualizations,
        )

    async def _run_ai_layer(
        self, repository_metadata, static_analysis_result, git_history_result, repository_metrics_result, analytics_result,
        advanced_visualizations=None,
    ) -> Optional[AIInsightsResult]:
        """
        Run the AI Layer on the already-computed Modules 1-6 outputs.

        AI is an enhancement over data that was successfully computed, so a
        failure here yields a structured partial result (status=unavailable)
        instead of failing the whole request and discarding Modules 1-6.
        """
        if self._ai_service is None:
            return None
        try:
            result = await self._ai_service.generate_insights(
                repository_metadata=repository_metadata,
                static_analysis_result=static_analysis_result,
                git_history_result=git_history_result,
                repository_metrics_result=repository_metrics_result,
                analytics_result=analytics_result,
                advanced_visualizations=advanced_visualizations,
            )
        except AIServiceError as exc:
            logger.error("[ORCHESTRATOR] AI Layer: Insights unavailable (%s)", type(exc).__name__)
            code = {OllamaUnavailableError: "AI_SERVICE_UNAVAILABLE", AIInvalidResponseError: "AI_INVALID_RESPONSE"}.get(
                type(exc), "AI_ERROR"
            )
            return self._unavailable(code, exc.message)
        except Exception:  # noqa: BLE001 - AI must never corrupt the response; logged in full server-side
            logger.exception("[ORCHESTRATOR] AI Layer: Insights failed unexpectedly")
            return self._unavailable("AI_ERROR", "AI insights could not be generated.")
        logger.info("[ORCHESTRATOR] AI Layer: Insights completed")
        return result

    @staticmethod
    def _unavailable(code: str, detail: str) -> AIInsightsResult:
        return AIInsightsResult(
            status=AIStatus.UNAVAILABLE,
            generated_at=datetime.now(timezone.utc),
            error=AIErrorDetail(code=code, detail=detail),
        )
