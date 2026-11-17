"""Unit tests for app.utils.github_url_parser."""

import pytest

from app.core.exceptions import InvalidRepositoryURLError
from app.utils.github_url_parser import parse_owner_repo


@pytest.mark.parametrize(
    "url,expected_owner,expected_repo",
    [
        ("https://github.com/fastapi/fastapi", "fastapi", "fastapi"),
        ("https://github.com/fastapi/fastapi/", "fastapi", "fastapi"),
        ("https://github.com/fastapi/fastapi.git", "fastapi", "fastapi"),
        ("http://github.com/fastapi/fastapi", "fastapi", "fastapi"),
        ("www.github.com/fastapi/fastapi", "fastapi", "fastapi"),
        ("github.com/fastapi/fastapi", "fastapi", "fastapi"),
        ("https://github.com/torvalds/linux", "torvalds", "linux"),
    ],
)
def test_parse_owner_repo_valid_urls(url: str, expected_owner: str, expected_repo: str) -> None:
    owner, repo = parse_owner_repo(url)
    assert owner == expected_owner
    assert repo == expected_repo


@pytest.mark.parametrize(
    "invalid_url",
    [
        "",
        "   ",
        "not-a-url",
        "https://gitlab.com/owner/repo",
        "https://github.com/owner-only",
        "https://github.com/",
    ],
)
def test_parse_owner_repo_invalid_urls(invalid_url: str) -> None:
    with pytest.raises(InvalidRepositoryURLError):
        parse_owner_repo(invalid_url)
