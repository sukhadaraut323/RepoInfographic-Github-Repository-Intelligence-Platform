"""
DocumentationAnalyzer — Module 5 component.

Scores a repository's documentation completeness by checking for the
presence of well-known documentation artifacts within the directory tree
already produced by Module 3 (`StaticAnalysisResult.directory_tree`).
No filesystem access happens here — this is a pure, rule-based
transformation of structured data already collected upstream.
"""

import logging

from app.schemas.metrics import SubScore
from app.schemas.static_analysis import StaticAnalysisResult
from app.utils.directory_tree_utils import directory_exists, find_matching_path

logger = logging.getLogger(__name__)

# Weighted checks, summing to 100.
_README_NAMES = ["README.md", "README.rst", "README.txt", "README"]
_LICENSE_NAMES = ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md"]
_CONTRIBUTING_NAMES = ["CONTRIBUTING.md", "CONTRIBUTING.rst", "CONTRIBUTING.txt", "CONTRIBUTING"]
_CHANGELOG_NAMES = ["CHANGELOG.md", "CHANGELOG.rst", "CHANGES.md", "HISTORY.md", "CHANGELOG"]
_DOCS_DIRECTORY_NAMES = ["docs", "doc", "documentation"]
_API_DOC_MARKERS = ["mkdocs.yml", "mkdocs.yaml", "conf.py", "openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json"]

_README_WEIGHT = 30
_LICENSE_WEIGHT = 20
_CONTRIBUTING_WEIGHT = 15
_CHANGELOG_WEIGHT = 15
_DOCS_FOLDER_WEIGHT = 10
_API_DOCS_WEIGHT = 10


class DocumentationAnalyzer:
    """Computes the Documentation Score from Module 3's directory tree."""

    def analyze(self, static_analysis_result: StaticAnalysisResult) -> SubScore:
        """Score documentation completeness (0-100) with evidence and reasons."""
        tree = static_analysis_result.directory_tree
        evidence: list[str] = []
        reasons: list[str] = []
        score = 0.0

        readme_path = find_matching_path(tree, _README_NAMES, only_top_level=True)
        if readme_path:
            score += _README_WEIGHT
            evidence.append(f"README found at '{readme_path}'.")
        else:
            evidence.append("No README file found at the repository root.")
            reasons.append(f"Missing README (-{_README_WEIGHT} pts).")

        license_path = find_matching_path(tree, _LICENSE_NAMES, only_top_level=True)
        if license_path:
            score += _LICENSE_WEIGHT
            evidence.append(f"LICENSE found at '{license_path}'.")
        else:
            evidence.append("No LICENSE file found at the repository root.")
            reasons.append(f"Missing LICENSE (-{_LICENSE_WEIGHT} pts).")

        contributing_path = find_matching_path(tree, _CONTRIBUTING_NAMES, only_top_level=True)
        if contributing_path:
            score += _CONTRIBUTING_WEIGHT
            evidence.append(f"CONTRIBUTING guide found at '{contributing_path}'.")
        else:
            evidence.append("No CONTRIBUTING guide found.")
            reasons.append(f"Missing CONTRIBUTING guide (-{_CONTRIBUTING_WEIGHT} pts).")

        changelog_path = find_matching_path(tree, _CHANGELOG_NAMES, only_top_level=True)
        if changelog_path:
            score += _CHANGELOG_WEIGHT
            evidence.append(f"CHANGELOG found at '{changelog_path}'.")
        else:
            evidence.append("No CHANGELOG found.")
            reasons.append(f"Missing CHANGELOG (-{_CHANGELOG_WEIGHT} pts).")

        docs_dir_path = directory_exists(tree, _DOCS_DIRECTORY_NAMES)
        if docs_dir_path:
            score += _DOCS_FOLDER_WEIGHT
            evidence.append(f"Documentation folder found at '{docs_dir_path}'.")
        else:
            evidence.append("No dedicated documentation folder found.")
            reasons.append(f"Missing docs folder (-{_DOCS_FOLDER_WEIGHT} pts).")

        has_api_docs = self._has_api_docs(static_analysis_result)
        if has_api_docs:
            score += _API_DOCS_WEIGHT
            evidence.append("API documentation tooling detected (e.g. mkdocs/sphinx/openapi config).")
        else:
            evidence.append("No API documentation tooling detected.")
            reasons.append(f"Missing API documentation tooling (-{_API_DOCS_WEIGHT} pts).")

        logger.debug("Documentation score computed: %.2f", score)
        return SubScore(score=round(score, 2), evidence=evidence, reasons=reasons)

    @staticmethod
    def _has_api_docs(static_analysis_result: StaticAnalysisResult) -> bool:
        """Detect common API/reference documentation tooling markers anywhere in the tree."""
        tree = static_analysis_result.directory_tree
        return find_matching_path(tree, _API_DOC_MARKERS, only_top_level=False) is not None
