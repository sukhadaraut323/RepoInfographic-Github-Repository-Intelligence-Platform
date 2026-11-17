"""
DocumentationAnalyzer — Module 5 component.

Scores a repository's documentation completeness using the reliable
marker-file facts Module 3 computed from its complete file scan
(`StaticAnalysisResult.marker_files`) — not the depth/entry-limited
`directory_tree`, which can produce false negatives for larger or
unusually-shaped repositories. No filesystem access happens here.
"""

import logging

from app.schemas.metrics import SubScore
from app.schemas.static_analysis import StaticAnalysisResult

logger = logging.getLogger(__name__)

# Weighted checks, summing to 100.
_README_WEIGHT = 30
_LICENSE_WEIGHT = 20
_CONTRIBUTING_WEIGHT = 15
_CHANGELOG_WEIGHT = 15
_DOCS_FOLDER_WEIGHT = 10
_API_DOCS_WEIGHT = 10


class DocumentationAnalyzer:
    """Computes the Documentation Score from Module 3's reliable marker-file facts."""

    def analyze(self, static_analysis_result: StaticAnalysisResult) -> SubScore:
        """Score documentation completeness (0-100) with evidence and reasons."""
        markers = static_analysis_result.marker_files
        evidence: list[str] = []
        reasons: list[str] = []
        score = 0.0

        if markers.readme.present:
            score += _README_WEIGHT
            evidence.append(f"README found at '{markers.readme.path}'.")
        else:
            evidence.append("No README file found at the repository root.")
            reasons.append(f"Missing README (-{_README_WEIGHT} pts).")

        if markers.license.present:
            score += _LICENSE_WEIGHT
            evidence.append(f"LICENSE found at '{markers.license.path}'.")
        else:
            evidence.append("No LICENSE file found at the repository root.")
            reasons.append(f"Missing LICENSE (-{_LICENSE_WEIGHT} pts).")

        if markers.contributing.present:
            score += _CONTRIBUTING_WEIGHT
            evidence.append(f"CONTRIBUTING guide found at '{markers.contributing.path}'.")
        else:
            evidence.append("No CONTRIBUTING guide found.")
            reasons.append(f"Missing CONTRIBUTING guide (-{_CONTRIBUTING_WEIGHT} pts).")

        if markers.changelog.present:
            score += _CHANGELOG_WEIGHT
            evidence.append(f"CHANGELOG found at '{markers.changelog.path}'.")
        else:
            evidence.append("No CHANGELOG found.")
            reasons.append(f"Missing CHANGELOG (-{_CHANGELOG_WEIGHT} pts).")

        if markers.has_docs_directory:
            score += _DOCS_FOLDER_WEIGHT
            evidence.append("Documentation folder found.")
        else:
            evidence.append("No dedicated documentation folder found.")
            reasons.append(f"Missing docs folder (-{_DOCS_FOLDER_WEIGHT} pts).")

        if markers.has_api_docs_tooling:
            score += _API_DOCS_WEIGHT
            evidence.append("API documentation tooling detected (e.g. mkdocs/sphinx/openapi config).")
        else:
            evidence.append("No API documentation tooling detected.")
            reasons.append(f"Missing API documentation tooling (-{_API_DOCS_WEIGHT} pts).")

        logger.debug("Documentation score computed: %.2f", score)
        return SubScore(score=round(score, 2), evidence=evidence, reasons=reasons)
