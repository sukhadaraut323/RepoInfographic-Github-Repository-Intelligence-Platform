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
    # Retry transient clone failures (network resets, stalled transfers) this
    # many times total before giving up. Does not apply to permanent failures
    # (repository not found, private, auth required).
    clone_max_attempts: int = 3
    clone_retry_backoff_seconds: float = 2.0
    # git -c http.postBuffer: negotiation buffer size in bytes. GitHub's Smart
    # HTTP transport resetting mid-transfer ("early EOF", "invalid index-pack
    # output") on larger repositories is commonly resolved by enlarging this
    # past its small 1 MiB default.
    clone_http_post_buffer_bytes: int = 524_288_000  # 500 MiB
    # git -c http.lowSpeedLimit / http.lowSpeedTime: abort a transfer that
    # stays below this throughput (bytes/sec) for this many seconds, so a
    # stalled (not just reset) connection cannot hang a request indefinitely.
    clone_http_low_speed_limit_bytes: int = 1000
    clone_http_low_speed_time_seconds: int = 30
    # After all full-clone retries are exhausted on a still-transient failure,
    # try one `--filter=blob:none` partial clone as a last resort: it keeps
    # the complete commit history (everything Git History Analysis needs)
    # while deferring file-content downloads, avoiding the large single-shot
    # transfer that is typically what triggers these resets in the first place.
    clone_partial_clone_fallback_enabled: bool = True

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
    # Cap on README characters read into readme_content (keeps huge READMEs
    # from bloating the response and the AI prompt).
    static_analysis_readme_max_chars: int = 6000

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
    # Above this many raw monthly points, the commit timeline chart
    # aggregates by year instead, so sparse long-lived histories remain
    # visually readable (lots of zero-filled months otherwise drown out
    # the real signal). Kept high (240 months = 20 years) so normal
    # repositories always retain monthly granularity in the chart; this is
    # a safety mechanism for pathological cases, not the common path - the
    # CommitTimelineFormatter mechanism itself is unchanged, only its
    # default threshold moved. The frontend handles X-axis label density
    # for long monthly series instead of the backend collapsing the data.
    analytics_commit_timeline_monthly_point_limit: int = 240
    analytics_health_status_excellent_threshold: float = 85.0
    analytics_health_status_good_threshold: float = 70.0
    analytics_health_status_fair_threshold: float = 50.0

    # --- AI Layer (Ollama) configuration ---
    # The Ollama model is configured here (env: OLLAMA_MODEL) and nowhere else.
    ai_enabled: bool = True
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    # Max SILENCE from Ollama (covers prompt processing before the first token,
    # then the gap between streamed chunks). Not a limit on total generation time.
    ollama_timeout_seconds: float = 300.0
    # Hard ceiling on one whole generation, so a stuck run still ends.
    ollama_total_timeout_seconds: float = 900.0
    ollama_temperature: float = 0.2
    # Explicit context window so the prompt is never silently truncated at
    # Ollama's (smaller) default, and a cap on generated tokens.
    ollama_num_ctx: int = 8192
    ollama_num_predict: int = 6000

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
