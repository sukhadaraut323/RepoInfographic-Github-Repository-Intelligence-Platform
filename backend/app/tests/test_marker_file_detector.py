"""
Tests for MarkerFileDetector, plus two regression tests reproducing the
real root causes found for inconsistent README/Dockerfile/docker-compose
detection:

1. `test_root_files_detected_even_when_many_top_level_directories_would_truncate_the_display_tree`
   reproduces the entry-count truncation bug: a repository root with more
   directories than `tree_max_entries_per_level` used to push root files
   (README, Dockerfile) out of the display tree entirely, so searching
   that tree for them (the old implementation) returned false negatives.
   Detection now comes from the complete file scan instead, so it is
   unaffected by tree truncation.

2. `test_one_unreadable_entry_does_not_hide_other_real_files_in_the_same_directory`
   reproduces the silent-wipeout bug: a single OSError while listing one
   entry used to blank out `entries = []` for the *whole* directory level,
   hiding every other real file (including README) alongside it.

Both are run against a real temp filesystem through the real
`RepositoryScanner`, not synthetic tree fixtures, since the bugs are in
how the scanner reads the real filesystem.
"""

import os
from pathlib import Path

import pytest

from app.services.marker_file_detector import MarkerFileDetector
from app.services.repository_scanner import RepositoryScanner

DETECTOR = MarkerFileDetector(readme_max_chars=6000)


def _scan(root: Path, tree_max_entries_per_level: int = 50):
    scanner = RepositoryScanner(ignored_directories=[".git"], tree_max_depth=3, tree_max_entries_per_level=tree_max_entries_per_level)
    return scanner.scan(root)


def test_detects_readme_license_dockerfile_at_root(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Hi\n")
    (tmp_path / "LICENSE").write_text("MIT\n")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n")

    scan = _scan(tmp_path)
    markers, readme_content, truncated = DETECTOR.detect(tmp_path, scan.files, scan.directories)

    assert markers.readme.present and markers.readme.path == "README.md"
    assert markers.license.present and markers.license.path == "LICENSE"
    assert markers.dockerfile.present and markers.dockerfile.path == "Dockerfile"
    assert markers.docker_compose.present and markers.docker_compose.path == "docker-compose.yml"
    assert readme_content == "# Hi\n"
    assert truncated is False


def test_detection_is_case_insensitive(tmp_path: Path) -> None:
    (tmp_path / "readme.MD").write_text("hi\n")
    scan = _scan(tmp_path)
    markers, _content, _trunc = DETECTOR.detect(tmp_path, scan.files, scan.directories)
    assert markers.readme.present is True


def test_nothing_present_reports_absent(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print(1)\n")
    scan = _scan(tmp_path)
    markers, readme_content, _trunc = DETECTOR.detect(tmp_path, scan.files, scan.directories)
    assert markers.readme.present is False and markers.readme.path is None
    assert readme_content is None


def test_ci_detected_via_github_workflows_directory(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\n")
    scan = _scan(tmp_path)
    markers, _c, _t = DETECTOR.detect(tmp_path, scan.files, scan.directories)
    assert markers.has_ci_config is True


def test_ci_detected_via_circleci_directory(tmp_path: Path) -> None:
    (tmp_path / ".circleci").mkdir()
    (tmp_path / ".circleci" / "config.yml").write_text("version: 2\n")
    scan = _scan(tmp_path)
    markers, _c, _t = DETECTOR.detect(tmp_path, scan.files, scan.directories)
    assert markers.has_ci_config is True


def test_ci_detected_via_travis_file(tmp_path: Path) -> None:
    (tmp_path / ".travis.yml").write_text("language: python\n")
    scan = _scan(tmp_path)
    markers, _c, _t = DETECTOR.detect(tmp_path, scan.files, scan.directories)
    assert markers.has_ci_config is True


def test_readme_content_truncated_at_configured_cap(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("x" * 100)
    detector = MarkerFileDetector(readme_max_chars=10)
    scan = _scan(tmp_path)
    _markers, content, truncated = detector.detect(tmp_path, scan.files, scan.directories)
    assert content == "x" * 10
    assert truncated is True


def test_unreadable_readme_yields_no_content_but_does_not_crash(tmp_path: Path) -> None:
    # A file with undecodable bytes under utf-8 strict decoding.
    (tmp_path / "README.md").write_bytes(b"\xff\xfe\x00binary garbage")
    scan = _scan(tmp_path)
    markers, content, truncated = DETECTOR.detect(tmp_path, scan.files, scan.directories)
    assert markers.readme.present is True  # presence is independent of readability
    assert content is None
    assert truncated is False


def test_root_files_detected_even_when_many_top_level_directories_would_truncate_the_display_tree(tmp_path: Path) -> None:
    """Regression test for the entry-count truncation root cause."""
    # 60 top-level directories > tree_max_entries_per_level (set to 50 below),
    # so the OLD implementation (searching directory_tree) would never see
    # README.md / Dockerfile, since directories sort first and already fill
    # every available slot before any root file is considered.
    for i in range(60):
        (tmp_path / f"package_{i:02d}").mkdir()
    (tmp_path / "README.md").write_text("# Monorepo\n")
    (tmp_path / "Dockerfile").write_text("FROM node:20\n")

    scan = _scan(tmp_path, tree_max_entries_per_level=50)

    # Confirm the display tree really is truncated and does NOT contain the root files
    # (proving this test actually reproduces the original failure condition).
    tree_child_names = {c.name for c in scan.directory_tree.children}
    assert scan.directory_tree.truncated is True
    assert "README.md" not in tree_child_names

    # The detector, using the complete file list, still finds them.
    markers, readme_content, _truncated = DETECTOR.detect(tmp_path, scan.files, scan.directories)
    assert markers.readme.present is True
    assert markers.readme.path == "README.md"
    assert markers.dockerfile.present is True
    assert readme_content == "# Monorepo\n"


def test_one_unreadable_entry_does_not_hide_other_real_files_in_the_same_directory(tmp_path: Path) -> None:
    """Regression test for the silent-whole-level-wipeout root cause."""
    (tmp_path / "README.md").write_text("# Project\n")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")
    broken_link = tmp_path / "broken-link"
    os.symlink(tmp_path / "does-not-exist", broken_link)

    scan = _scan(tmp_path)

    # The directory tree must still contain the real files, not an empty level.
    tree_child_names = {c.name for c in scan.directory_tree.children}
    assert "README.md" in tree_child_names
    assert "Dockerfile" in tree_child_names

    markers, readme_content, _truncated = DETECTOR.detect(tmp_path, scan.files, scan.directories)
    assert markers.readme.present is True
    assert markers.dockerfile.present is True
    assert readme_content == "# Project\n"
