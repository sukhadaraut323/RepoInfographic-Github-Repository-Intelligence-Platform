"""
MarkerFileDetector — Module 3 component.

Detects well-known repository marker files (README, LICENSE, Dockerfile,
CI config, etc.) and reads README content, directly from the *complete*
file list `RepositoryScanner.scan()` already collected — not from the
depth/entry-limited `directory_tree` built for display purposes.

This exists because the display tree is deliberately shallow and capped
(see `RepositoryScanner`), so searching it for marker files can produce
false negatives for larger or unusually-shaped repositories. The raw
`scan_result.files`/`directories` lists have no such limit: every file
Module 3 actually found on disk is in them. Using them here is what makes
marker-file detection deterministic regardless of repository size.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from app.schemas.static_analysis import RepositoryMarkerFiles, RootMarkerFile

logger = logging.getLogger(__name__)

_README_NAMES = {"readme.md", "readme.rst", "readme.txt", "readme.markdown", "readme.adoc", "readme"}
_LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "copying.md"}
_CONTRIBUTING_NAMES = {"contributing.md", "contributing.rst", "contributing.txt", "contributing"}
_CHANGELOG_NAMES = {"changelog.md", "changelog.rst", "changes.md", "history.md", "changelog"}
_DOCKERFILE_NAMES = {"dockerfile"}
_DOCKER_COMPOSE_NAMES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
_GITIGNORE_NAMES = {".gitignore"}
_EDITORCONFIG_NAMES = {".editorconfig"}
_ENV_EXAMPLE_NAMES = {".env.example", ".env.sample", "env.example"}
_PRECOMMIT_NAMES = {".pre-commit-config.yaml", ".pre-commit-config.yml"}
_CI_CONFIG_FILE_NAMES = {".travis.yml", ".gitlab-ci.yml", "azure-pipelines.yml"}
_CI_CONFIG_DIR_NAMES = {".circleci"}
_DOCS_DIR_NAMES = {"docs", "doc", "documentation"}
_API_DOC_MARKER_NAMES = {"mkdocs.yml", "mkdocs.yaml", "conf.py", "openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json"}


class MarkerFileDetector:
    """Computes `RepositoryMarkerFiles` and reads README content from a complete file scan."""

    def __init__(self, readme_max_chars: int) -> None:
        self._readme_max_chars = readme_max_chars

    def detect(
        self, root: Path, files: List[Path], directories: List[Path]
    ) -> Tuple[RepositoryMarkerFiles, Optional[str], bool]:
        """
        Returns (marker_files, readme_content, readme_truncated).

        `files`/`directories` must be the complete, untruncated lists from
        `RepositoryScanner.scan()` (already ignore-rule-filtered).
        """
        root_files = [f for f in files if f.parent == root]

        readme = self._find_root(root_files, root, _README_NAMES)
        license_ = self._find_root(root_files, root, _LICENSE_NAMES)
        contributing = self._find_root(root_files, root, _CONTRIBUTING_NAMES)
        changelog = self._find_root(root_files, root, _CHANGELOG_NAMES)
        dockerfile = self._find_root(root_files, root, _DOCKERFILE_NAMES)
        docker_compose = self._find_root(root_files, root, _DOCKER_COMPOSE_NAMES)
        gitignore = self._find_root(root_files, root, _GITIGNORE_NAMES)
        editorconfig = self._find_root(root_files, root, _EDITORCONFIG_NAMES)
        env_example = self._find_root(root_files, root, _ENV_EXAMPLE_NAMES)
        precommit = self._find_root(root_files, root, _PRECOMMIT_NAMES)

        has_ci = (
            any(f.parent == root and f.name.lower() in _CI_CONFIG_FILE_NAMES for f in files)
            or any(d.parent == root and d.name.lower() in _CI_CONFIG_DIR_NAMES for d in directories)
            or self._has_github_workflows(files, root)
        )
        has_docs_dir = any(d.parent == root and d.name.lower() in _DOCS_DIR_NAMES for d in directories)
        has_api_docs = any(f.name.lower() in _API_DOC_MARKER_NAMES for f in files)

        marker_files = RepositoryMarkerFiles(
            readme=readme,
            license=license_,
            contributing=contributing,
            changelog=changelog,
            dockerfile=dockerfile,
            docker_compose=docker_compose,
            gitignore=gitignore,
            editorconfig=editorconfig,
            env_example=env_example,
            precommit_config=precommit,
            has_ci_config=has_ci,
            has_docs_directory=has_docs_dir,
            has_api_docs_tooling=has_api_docs,
        )

        readme_content, readme_truncated = self._read_readme(readme, root)
        return marker_files, readme_content, readme_truncated

    @staticmethod
    def _find_root(root_files: List[Path], root: Path, candidate_names: set) -> RootMarkerFile:
        for f in root_files:
            if f.name.lower() in candidate_names:
                return RootMarkerFile(present=True, path=str(f.relative_to(root)))
        return RootMarkerFile(present=False, path=None)

    @staticmethod
    def _has_github_workflows(files: List[Path], root: Path) -> bool:
        workflows_dir = root / ".github" / "workflows"
        return any(
            f.parent == workflows_dir and f.suffix.lower() in (".yml", ".yaml") for f in files
        )

    def _read_readme(self, readme: RootMarkerFile, root: Path) -> Tuple[Optional[str], bool]:
        if not readme.present or not readme.path:
            return None, False
        try:
            full_path = root / readme.path
            text = full_path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("README detected at %s but could not be read as text: %s", readme.path, exc)
            return None, False

        if len(text) > self._readme_max_chars:
            return text[: self._readme_max_chars], True
        return text, False
