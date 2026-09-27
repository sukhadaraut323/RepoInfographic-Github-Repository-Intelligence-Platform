"""
Application configuration.

Loads settings from environment variables (via a local .env file in
development). No secrets are hardcoded anywhere in the codebase — the
GitHub token is read exclusively from the environment.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    # --- GitHub API configuration ---
    github_token: str
    github_api_base_url: str = "https://api.github.com"
    github_api_timeout_seconds: float = 10.0

    # --- Application configuration ---
    log_level: str = "INFO"
    app_name: str = "GitHub Repository Intelligence Platform"
    api_v1_prefix: str = "/api/v1"

    # --- Repository Cloner (Module 2) configuration ---
    workspace_directory: str = "./workspace"

    # --- Static Code Analysis (Module 3) configuration ---
    static_analysis_ignored_directories: List[str] = Field(
        default_factory=lambda: [
            ".git",
            "node_modules",
            "venv",
            "__pycache__",
            "dist",
            "build",
            ".idea",
            ".vscode",
            "coverage",
        ]
    )
    static_analysis_max_file_size_bytes: int = 2_000_000
    static_analysis_tree_max_depth: int = 3
    static_analysis_tree_max_entries_per_level: int = 50

    # --- Git History Analysis (Module 4) configuration ---
    git_history_activity_window_days: int = 30
    git_history_high_activity_threshold: int = 20
    git_history_medium_activity_threshold: int = 5
    git_history_low_activity_threshold: int = 1

    # --- Engineering Metrics Engine (Module 5) configuration ---
    # Weights applied by HealthScoreCalculator when combining the six
    # sub-scores into the overall health score. Should sum to 1.0.
    metrics_weight_documentation: float = 0.15
    metrics_weight_codebase: float = 0.20
    metrics_weight_activity: float = 0.20
    metrics_weight_community: float = 0.15
    metrics_weight_maintainability: float = 0.15
    metrics_weight_best_practices: float = 0.15

    # --- Analytics Engine (Module 6) configuration ---
    analytics_largest_directories_limit: int = 10
    analytics_health_status_excellent_threshold: float = 85.0
    analytics_health_status_good_threshold: float = 70.0
    analytics_health_status_fair_threshold: float = 50.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Using lru_cache avoids re-parsing the .env file on every request while
    still allowing Settings to be imported/instantiated lazily (important
    for testability — settings can be overridden via dependency overrides).
    """
    return Settings()
