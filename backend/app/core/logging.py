"""
Centralized logging configuration for the application.

Call `configure_logging()` once at application startup (see app/main.py).
Every module then obtains a logger via `logging.getLogger(__name__)`.
"""

import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure the root logger with a consistent, readable format."""
    settings = get_settings()

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    logging.basicConfig(
        level=settings.log_level.upper(),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # ensures reconfiguration works cleanly in tests
    )

    # Third-party libraries are noisy at DEBUG/INFO — keep them at WARNING
    # unless the application itself is running in DEBUG mode.
    if settings.log_level.upper() != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
