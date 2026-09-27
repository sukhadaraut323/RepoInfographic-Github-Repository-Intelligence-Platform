"""
Application entry point.

Run locally with:
    uvicorn app.main:app --reload

Swagger UI is available at /docs and ReDoc at /redoc.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown hook."""
    logger.info("%s starting up.", settings.app_name)
    yield
    logger.info("%s shutting down.", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-Powered GitHub Repository Intelligence Platform - "
        "Module 1: GitHub Repository Metadata Collector."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Health"], summary="Service health check")
async def health_check() -> dict:
    """Basic liveness probe for the API."""
    return {"status": "ok"}
