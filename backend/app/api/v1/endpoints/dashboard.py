"""
API endpoint for the Repository Orchestrator.

Exposes the single production entry point for the frontend:
    POST /api/v1/dashboard/analyze

This is the only endpoint the production frontend should call. The
per-module endpoints (Modules 1-6) remain available for development,
testing, and debugging, unchanged.

Unlike Modules 1-6's endpoints (which return their raw result schema
directly), this endpoint wraps its response in the standard
`{success, message, data}` / `{success, message, error}` envelope defined
by the API Contract. To keep that envelope fully local to this new
endpoint - without adding a global exception handler that would alter
Modules 1-6's existing (stable) error response shape - errors are caught
and formatted here rather than via `HTTPException`.
"""

import logging
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.analytics import get_analytics_service
from app.api.v1.endpoints.clone import get_repository_cloner_service
from app.api.v1.endpoints.git_history import get_git_history_service
from app.api.v1.endpoints.metrics import get_repository_metrics_service
from app.api.v1.endpoints.repository import get_repository_service
from app.api.v1.endpoints.static_analysis import get_static_analysis_service
from app.clients.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.exceptions import (
    AppException,
    GitHistoryAnalysisError,
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitExceededError,
    InvalidGitReferenceError,
    InvalidRepositoryURLError,
    NotAGitRepositoryError,
    RepositoryCloneError,
    RepositoryNotFoundError,
    RepositoryPathNotFoundError,
    StaticAnalysisError,
)
from app.schemas.dashboard import (
    DashboardAnalyzeErrorResponse,
    DashboardAnalyzeRequest,
    DashboardAnalyzeSuccessResponse,
    DashboardErrorDetail,
    DashboardReportRequest,
)
from app.services.ai_insights_service import AIInsightsService
from app.services.repository_orchestrator_service import RepositoryOrchestratorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Repository Orchestrator"])

# Each downstream AppException mapped to (HTTP status, stable error code).
# Mirrors the exact status codes each module's own endpoint already uses.
_ERROR_MAP = {
    InvalidRepositoryURLError: (status.HTTP_400_BAD_REQUEST, "INVALID_REPOSITORY_URL"),
    RepositoryNotFoundError: (status.HTTP_404_NOT_FOUND, "REPOSITORY_NOT_FOUND"),
    GitHubAuthenticationError: (status.HTTP_502_BAD_GATEWAY, "GITHUB_AUTHENTICATION_ERROR"),
    GitHubRateLimitExceededError: (status.HTTP_429_TOO_MANY_REQUESTS, "GITHUB_RATE_LIMIT_EXCEEDED"),
    GitHubAPIError: (status.HTTP_502_BAD_GATEWAY, "GITHUB_API_ERROR"),
    InvalidGitReferenceError: (status.HTTP_400_BAD_REQUEST, "INVALID_GIT_REFERENCE"),
    RepositoryCloneError: (status.HTTP_502_BAD_GATEWAY, "REPOSITORY_CLONE_ERROR"),
    RepositoryPathNotFoundError: (status.HTTP_404_NOT_FOUND, "REPOSITORY_PATH_NOT_FOUND"),
    NotAGitRepositoryError: (status.HTTP_400_BAD_REQUEST, "NOT_A_GIT_REPOSITORY"),
    StaticAnalysisError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "STATIC_ANALYSIS_ERROR"),
    GitHistoryAnalysisError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "GIT_HISTORY_ANALYSIS_ERROR"),
}


def get_ai_insights_service() -> Optional[AIInsightsService]:
    """Dependency provider for the AI Layer; None when AI_ENABLED=false."""
    settings = get_settings()
    if not settings.ai_enabled:
        return None
    return AIInsightsService(ollama_client=OllamaClient(settings))


def get_repository_orchestrator_service() -> RepositoryOrchestratorService:
    """
    Dependency provider for RepositoryOrchestratorService.

    Reuses each module's own existing dependency provider function rather
    than re-constructing their services, so every module's configuration
    (settings, thresholds, weights, etc.) continues to live in exactly one
    place. Kept as a function (rather than a module-level singleton) so
    tests can override it via `app.dependency_overrides`.
    """
    return RepositoryOrchestratorService(
        repository_service=get_repository_service(),
        repository_cloner_service=get_repository_cloner_service(),
        static_analysis_service=get_static_analysis_service(),
        git_history_service=get_git_history_service(),
        repository_metrics_service=get_repository_metrics_service(),
        analytics_service=get_analytics_service(),
        ai_service=get_ai_insights_service(),
    )


def _error_response(exc: AppException) -> JSONResponse:
    """Map a known AppException into the standard error envelope."""
    http_status, code = _ERROR_MAP.get(type(exc), (status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR"))
    body = DashboardAnalyzeErrorResponse(
        message="Repository analysis failed.",
        error=DashboardErrorDetail(code=code, detail=exc.message),
    )
    return JSONResponse(status_code=http_status, content=body.model_dump(mode="json"))


@router.post(
    "/analyze",
    response_model=DashboardAnalyzeSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the complete Modules 1-6 pipeline for a GitHub repository URL",
    description=(
        "The single production entry point for the frontend. Given a "
        "public GitHub repository URL, orchestrates Modules 1-6 in "
        "dependency order (Metadata -> Clone -> Static Analysis -> Git "
        "History -> Engineering Metrics -> Analytics) via direct Python "
        "service calls and returns one unified, structured dashboard "
        "response. No internal HTTP requests are made and no module's "
        "business logic is duplicated."
    ),
    responses={
        400: {"model": DashboardAnalyzeErrorResponse},
        404: {"model": DashboardAnalyzeErrorResponse},
        429: {"model": DashboardAnalyzeErrorResponse},
        500: {"model": DashboardAnalyzeErrorResponse},
        502: {"model": DashboardAnalyzeErrorResponse},
    },
)
async def analyze_dashboard(
    request: DashboardAnalyzeRequest,
    service: RepositoryOrchestratorService = Depends(get_repository_orchestrator_service),
):
    """Run the full repository analysis pipeline and return the unified dashboard payload."""
    try:
        data = await service.analyze(request.repository_url)
    except tuple(_ERROR_MAP.keys()) as exc:  # type: ignore[misc]
        logger.warning("Dashboard analysis failed with %s: %s", type(exc).__name__, exc.message)
        return _error_response(exc)
    except AppException as exc:
        # Safety net for any AppException subtype not explicitly mapped
        # above (e.g. one added later by another module).
        logger.error("Unmapped application error during dashboard analysis: %s", exc.message)
        return _error_response(exc)
    except Exception:  # noqa: BLE001 - final safety net, never leaks internals
        logger.exception("Unexpected error during dashboard analysis.")
        body = DashboardAnalyzeErrorResponse(
            message="Repository analysis failed due to an unexpected internal error.",
            error=DashboardErrorDetail(code="INTERNAL_ERROR", detail="An unexpected internal error occurred."),
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body.model_dump(mode="json"))

    return DashboardAnalyzeSuccessResponse(
        message="Repository analysis completed successfully.",
        data=data,
    )


@router.post(
    "/report",
    summary="Generate a PDF report from a completed dashboard analysis",
    response_description="A downloadable PDF report generated from the supplied dashboard result.",
    responses={200: {"content": {"application/pdf": {}}}, 422: {"description": "Invalid or incomplete dashboard data."}},
)
async def generate_dashboard_report(request: DashboardReportRequest):
    """Generate a PDF from the exact analysis payload; never clone or re-run analysis."""
    from fastapi import HTTPException
    from fastapi.responses import Response
    from app.services.report_generation_service import ReportGenerationService
    import re

    try:
        payload = request.data.model_dump(mode="json")
        pdf = await asyncio.to_thread(ReportGenerationService().generate, payload)
    except Exception as exc:  # report failure must not affect dashboard analysis
        logger.exception("Dashboard PDF report generation failed")
        raise HTTPException(status_code=500, detail="The repository report could not be generated.") from exc
    full_name = payload.get("repository_metadata", {}).get("full_name", "repository")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", full_name.replace("/", "_" )).strip("._") or "repository"
    filename = f"RepoInfographic_{safe_name}_Analysis_Report.pdf"
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})
