"""
Shared pytest fixtures.

Sets a dummy GITHUB_TOKEN before any app module is imported, since
`Settings` requires it to be present. Tests never make real network calls
to GitHub — the GitHubClient is mocked/stubbed wherever needed.
"""

import os

os.environ.setdefault("GITHUB_TOKEN", "test-token-for-unit-tests")
