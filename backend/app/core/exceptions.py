"""
Custom exception hierarchy for the platform.

Keeping exceptions centralized in `core` allows every layer (clients,
services, api) to raise/catch consistent, well-typed errors instead of
leaking low-level library exceptions (e.g. httpx errors) up to the API
layer.
"""


class AppException(Exception):
    """Base class for all application-specific exceptions."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InvalidRepositoryURLError(AppException):
    """Raised when a supplied GitHub repository URL cannot be parsed."""


class RepositoryNotFoundError(AppException):
    """Raised when GitHub returns 404 for the requested repository."""


class GitHubAuthenticationError(AppException):
    """Raised when the configured GitHub token is missing/invalid (401)."""


class GitHubRateLimitExceededError(AppException):
    """Raised when GitHub API rate limits are exhausted (403/429)."""


class GitHubAPIError(AppException):
    """Raised for any other unexpected GitHub API failure."""


class RepositoryCloneError(AppException):
    """Raised when a git clone/fetch/pull operation fails (Module 2)."""


class InvalidGitReferenceError(AppException):
    """Raised when a requested branch does not exist locally or on the remote."""


class RepositoryPathNotFoundError(AppException):
    """Raised when the given local repository path does not exist or is not a directory (Module 3)."""


class StaticAnalysisError(AppException):
    """Raised when the static analysis scan fails unexpectedly (Module 3)."""


class NotAGitRepositoryError(AppException):
    """Raised when the given local path exists but is not a valid git repository (Module 4)."""


class GitHistoryAnalysisError(AppException):
    """Raised when git history cannot be read due to corrupted or unreadable metadata (Module 4)."""


class AIServiceError(AppException):
    """Base class for failures inside the AI Layer."""


class OllamaUnavailableError(AIServiceError):
    """Raised when Ollama cannot be reached, times out, or rejects the request."""


class AIInvalidResponseError(AIServiceError):
    """Raised when the AI model's output cannot be parsed into the expected structure."""
