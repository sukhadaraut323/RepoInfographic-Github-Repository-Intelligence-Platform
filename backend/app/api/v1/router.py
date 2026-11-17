"""
Aggregates all v1 endpoint routers.

As new modules are implemented, their routers will be included here.
Modules 1, 2, 3, 4, 5, and 6's routers are included today, along with the
Repository Orchestrator's dashboard router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import analytics, clone, dashboard, git_history, metrics, repository, static_analysis

api_router = APIRouter()
api_router.include_router(repository.router)
api_router.include_router(clone.router)
api_router.include_router(static_analysis.router)
api_router.include_router(git_history.router)
api_router.include_router(metrics.router)
api_router.include_router(analytics.router)
api_router.include_router(dashboard.router)
