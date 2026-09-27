"""
BestPracticesAnalyzer — Module 5 component.

Scores adherence to common engineering best practices by checking for
well-known configuration file markers within the directory tree already
produced by Module 3. No filesystem access happens here.
"""

import logging
from typing import List

from app.schemas.metrics import SubScore
from app.schemas.static_analysis import StaticAnalysisResult
from app.utils.directory_tree_utils import directory_exists, find_matching_path, path_exists_with_suffix

logger = logging.getLogger(__name__)

_CI_CONFIG_FILES = [".travis.yml", ".gitlab-ci.yml", "azure-pipelines.yml"]
_CI_CONFIG_DIRS = [".circleci"]
_DOCKERFILE_NAMES = ["Dockerfile"]
_DOCKER_COMPOSE_NAMES = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
_GITIGNORE_NAMES = [".gitignore"]
_EDITORCONFIG_NAMES = [".editorconfig"]
_ENV_EXAMPLE_NAMES = [".env.example", ".env.sample", "env.example"]
_PRECOMMIT_NAMES = [".pre-commit-config.yaml", ".pre-commit-config.yml"]

_CI_WEIGHT = 25
_DOCKER_WEIGHT = 15
_DOCKER_COMPOSE_WEIGHT = 10
_GITIGNORE_WEIGHT = 15
_EDITORCONFIG_WEIGHT = 10
_ENV_EXAMPLE_WEIGHT = 10
_PRECOMMIT_WEIGHT = 15


class BestPracticesAnalyzer:
    """Computes the Best Practices Score from Module 3's directory tree."""

    def analyze(self, static_analysis_result: StaticAnalysisResult) -> SubScore:
        """Score best-practice tooling adoption (0-100) with evidence and reasons."""
        tree = static_analysis_result.directory_tree
        evidence: List[str] = []
        reasons: List[str] = []
        score = 0.0

        has_ci = (
            path_exists_with_suffix(tree, ".github/workflows/", [".yml", ".yaml"])
            or find_matching_path(tree, _CI_CONFIG_FILES, only_top_level=True) is not None
            or directory_exists(tree, _CI_CONFIG_DIRS) is not None
        )
        if has_ci:
            score += _CI_WEIGHT
            evidence.append("CI configuration detected (GitHub Actions, Travis, CircleCI, GitLab CI, or Azure Pipelines).")
        else:
            evidence.append("No CI configuration detected.")
            reasons.append(f"Missing CI configuration (-{_CI_WEIGHT} pts).")

        dockerfile_path = find_matching_path(tree, _DOCKERFILE_NAMES, only_top_level=True)
        if dockerfile_path:
            score += _DOCKER_WEIGHT
            evidence.append(f"Dockerfile found at '{dockerfile_path}'.")
        else:
            evidence.append("No Dockerfile found.")
            reasons.append(f"Missing Dockerfile (-{_DOCKER_WEIGHT} pts).")

        compose_path = find_matching_path(tree, _DOCKER_COMPOSE_NAMES, only_top_level=True)
        if compose_path:
            score += _DOCKER_COMPOSE_WEIGHT
            evidence.append(f"Docker Compose file found at '{compose_path}'.")
        else:
            evidence.append("No Docker Compose file found.")
            reasons.append(f"Missing Docker Compose file (-{_DOCKER_COMPOSE_WEIGHT} pts).")

        gitignore_path = find_matching_path(tree, _GITIGNORE_NAMES, only_top_level=True)
        if gitignore_path:
            score += _GITIGNORE_WEIGHT
            evidence.append(f"'.gitignore' found at '{gitignore_path}'.")
        else:
            evidence.append("No '.gitignore' found.")
            reasons.append(f"Missing .gitignore (-{_GITIGNORE_WEIGHT} pts).")

        editorconfig_path = find_matching_path(tree, _EDITORCONFIG_NAMES, only_top_level=True)
        if editorconfig_path:
            score += _EDITORCONFIG_WEIGHT
            evidence.append(f"'.editorconfig' found at '{editorconfig_path}'.")
        else:
            evidence.append("No '.editorconfig' found.")
            reasons.append(f"Missing .editorconfig (-{_EDITORCONFIG_WEIGHT} pts).")

        env_example_path = find_matching_path(tree, _ENV_EXAMPLE_NAMES, only_top_level=True)
        if env_example_path:
            score += _ENV_EXAMPLE_WEIGHT
            evidence.append(f"Environment variable example file found at '{env_example_path}'.")
        else:
            evidence.append("No '.env.example' (or equivalent) found.")
            reasons.append(f"Missing .env.example (-{_ENV_EXAMPLE_WEIGHT} pts).")

        precommit_path = find_matching_path(tree, _PRECOMMIT_NAMES, only_top_level=True)
        if precommit_path:
            score += _PRECOMMIT_WEIGHT
            evidence.append(f"Pre-commit hook configuration found at '{precommit_path}'.")
        else:
            evidence.append("No pre-commit hook configuration found.")
            reasons.append(f"Missing pre-commit configuration (-{_PRECOMMIT_WEIGHT} pts).")

        logger.debug("Best practices score computed: %.2f", score)
        return SubScore(score=round(score, 2), evidence=evidence, reasons=reasons)
