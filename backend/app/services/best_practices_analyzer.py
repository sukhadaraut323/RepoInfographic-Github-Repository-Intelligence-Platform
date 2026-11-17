"""
BestPracticesAnalyzer — Module 5 component.

Scores adherence to common engineering best practices using the reliable
marker-file facts Module 3 computed from its complete file scan
(`StaticAnalysisResult.marker_files`) — not the depth/entry-limited
`directory_tree`. No filesystem access happens here.
"""

import logging
from typing import List

from app.schemas.metrics import SubScore
from app.schemas.static_analysis import StaticAnalysisResult

logger = logging.getLogger(__name__)

_CI_WEIGHT = 25
_DOCKER_WEIGHT = 15
_DOCKER_COMPOSE_WEIGHT = 10
_GITIGNORE_WEIGHT = 15
_EDITORCONFIG_WEIGHT = 10
_ENV_EXAMPLE_WEIGHT = 10
_PRECOMMIT_WEIGHT = 15


class BestPracticesAnalyzer:
    """Computes the Best Practices Score from Module 3's reliable marker-file facts."""

    def analyze(self, static_analysis_result: StaticAnalysisResult) -> SubScore:
        """Score best-practice tooling adoption (0-100) with evidence and reasons."""
        markers = static_analysis_result.marker_files
        evidence: List[str] = []
        reasons: List[str] = []
        score = 0.0

        if markers.has_ci_config:
            score += _CI_WEIGHT
            evidence.append("CI configuration detected (GitHub Actions, Travis, CircleCI, GitLab CI, or Azure Pipelines).")
        else:
            evidence.append("No CI configuration detected.")
            reasons.append(f"Missing CI configuration (-{_CI_WEIGHT} pts).")

        if markers.dockerfile.present:
            score += _DOCKER_WEIGHT
            evidence.append(f"Dockerfile found at '{markers.dockerfile.path}'.")
        else:
            evidence.append("No Dockerfile found.")
            reasons.append(f"Missing Dockerfile (-{_DOCKER_WEIGHT} pts).")

        if markers.docker_compose.present:
            score += _DOCKER_COMPOSE_WEIGHT
            evidence.append(f"Docker Compose file found at '{markers.docker_compose.path}'.")
        else:
            evidence.append("No Docker Compose file found.")
            reasons.append(f"Missing Docker Compose file (-{_DOCKER_COMPOSE_WEIGHT} pts).")

        if markers.gitignore.present:
            score += _GITIGNORE_WEIGHT
            evidence.append(f"'.gitignore' found at '{markers.gitignore.path}'.")
        else:
            evidence.append("No '.gitignore' found.")
            reasons.append(f"Missing .gitignore (-{_GITIGNORE_WEIGHT} pts).")

        if markers.editorconfig.present:
            score += _EDITORCONFIG_WEIGHT
            evidence.append(f"'.editorconfig' found at '{markers.editorconfig.path}'.")
        else:
            evidence.append("No '.editorconfig' found.")
            reasons.append(f"Missing .editorconfig (-{_EDITORCONFIG_WEIGHT} pts).")

        if markers.env_example.present:
            score += _ENV_EXAMPLE_WEIGHT
            evidence.append(f"Environment variable example file found at '{markers.env_example.path}'.")
        else:
            evidence.append("No '.env.example' (or equivalent) found.")
            reasons.append(f"Missing .env.example (-{_ENV_EXAMPLE_WEIGHT} pts).")

        if markers.precommit_config.present:
            score += _PRECOMMIT_WEIGHT
            evidence.append(f"Pre-commit hook configuration found at '{markers.precommit_config.path}'.")
        else:
            evidence.append("No pre-commit hook configuration found.")
            reasons.append(f"Missing pre-commit configuration (-{_PRECOMMIT_WEIGHT} pts).")

        logger.debug("Best practices score computed: %.2f", score)
        return SubScore(score=round(score, 2), evidence=evidence, reasons=reasons)
