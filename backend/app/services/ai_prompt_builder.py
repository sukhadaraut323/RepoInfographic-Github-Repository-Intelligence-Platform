"""
Prompt construction for the AI Layer.

Holds the controlled prompt template and the function that turns the
structured outputs of Modules 1-6 into a compact evidence payload. No
repository-specific facts live in this file - everything comes from the
supplied data. Internal filesystem paths are deliberately excluded.

Kept deliberately lean: Ollama generation time scales with prompt size, so
this builder favors the backend's own already-computed summary statistics
and evidence sentences (e.g. `engineering_metrics.documentation.evidence`)
over large raw arrays the model would otherwise have to read through
token-by-token for little added signal - see `monthly_commit_timeline`
below, a typical example of real signal drowned in mostly-zero padding.
"""

import json
from typing import Any, Dict

from app.schemas.analytics import AnalyticsDashboardResult
from app.schemas.git_history import GitHistoryResult
from app.schemas.metrics import RepositoryMetricsResult
from app.schemas.repository import RepositoryMetadata
from app.schemas.static_analysis import StaticAnalysisResult

SECTION_KEYS = (
    "repository_summary",
    "architecture_explanation",
    "contribution_guide",
    "project_evolution_roadmap",
    "learning_roadmap",
    "commit_suggestions",
    "improvement_suggestions",
    "readme_review",
)

_MAX_TOP_LEVEL_ENTRIES = 40
_MAX_FILE_TYPES = 10
_MAX_LANGUAGES = 15
# README is already capped at the source (StaticAnalysisService, via
# static_analysis_readme_max_chars) for the API response; this is a
# separate, smaller cap specifically for what goes into the AI prompt,
# since a long README is one of the biggest single contributors to slow
# generation for little extra benefit beyond the first couple of screens.
_MAX_README_CHARS_FOR_PROMPT = 2000

# Things the model is NOT given. Listed explicitly so it can report them as
# missing instead of guessing. "README text" is added dynamically below
# only when no README was actually found - when one exists, its content is
# supplied directly and must not be listed as unavailable.
_ALWAYS_NOT_PROVIDED = [
    "source code contents",
    "commit messages",
    "issue and pull request data",
    "dependency manifest contents",
]

SYSTEM_PROMPT = """You are an engineering analyst for the RepoInfographic platform.
You explain a GitHub repository using ONLY the structured evidence supplied in the user message.

Rules:
1. Never invent repository facts. Every observation must cite supplied values in its "evidence" list.
2. Keep observations (what the data shows) separate from recommendations (advice).
3. Anything listed under "not_provided" was NOT given to you. Do not describe it; report it under "missing_information".
4. Do not mark a whole section unavailable merely because source code or commit messages were not supplied. Use the available repository metadata, file structure, languages, metrics and README evidence. Clearly state limitations inside missing_information.
5. Always return all eight requested sections. Roadmaps and learning guidance can be generated from detected technologies and repository structure; label them as suggested next steps, not as facts about past work.
6. For README review, if no README exists, explicitly say it was not detected and provide concrete README content suggestions grounded in the repository metadata and detected technologies.
7. Be concrete and useful for a developer new to this repository. Do not pad.
8. Respond with a single complete JSON object and nothing else."""

OUTPUT_SPEC = """Return ONE JSON object with exactly these keys:
repository_summary, architecture_explanation, contribution_guide, project_evolution_roadmap,
learning_roadmap, commit_suggestions, improvement_suggestions, readme_review

Each key maps to an object with:
  "available": boolean
  "summary": string
  "observations": [ {"statement": string, "evidence": [string, ...]} ]
  "recommendations": [string, ...]
  "stages": [ {"level": string, "description": string, "items": [string, ...]} ]
  "missing_information": [string, ...]

Section guidance:
- repository_summary: what the repository is and how healthy/active it appears.
- architecture_explanation: how the codebase appears organised, from the directory and language evidence only.
- contribution_guide: where a newcomer could start, given the evidence.
- project_evolution_roadmap: always provide useful, repository-specific stages describing realistic next phases for THIS detected project; do not claim these phases already happened.
- learning_roadmap: use "stages" for what a learner should study to understand this repository.
- commit_suggestions: small, concrete first commits a contributor could make.
- improvement_suggestions: prioritised improvements tied to weak scores or gaps in the evidence.
- readme_review: if readme_content is present, review its actual content. If readme_available is false, say no README was detected, then suggest the specific sections this repository's README should contain based on supplied metadata and technologies.

RECOMMENDATIONS must each be ONE sentence that does all of the following, in this order, using only
supplied evidence - never a generic platitude:
  1. Start with a priority tag: "[High]", "[Medium]", or "[Low]".
  2. State the specific fact detected, citing a real number or name from the evidence.
  3. State briefly why it matters for this repository.
  4. State a concrete action.
Example of the required style - BAD (do not write like this): "Add a CONTRIBUTING guide."
GOOD (write like this): "[Medium] The repository has 53 contributors and 136 open issues but no
CONTRIBUTING.md, so new contributors lack guidance on branching and review workflow - add one covering
issue triage and PR expectations."
Never recommend something the evidence already shows is present.

Use an empty "stages" list for sections that are not roadmaps.

Return all eight sections. Aim for 3-5 observations and 3-5 recommendations when supported by evidence, and 3-5 stages for each roadmap. Keep content specific and readable; do not omit a section just to save tokens."""


def build_ai_input(
    repository_metadata: RepositoryMetadata,
    static_analysis_result: StaticAnalysisResult,
    git_history_result: GitHistoryResult,
    repository_metrics_result: RepositoryMetricsResult,
    analytics_result: AnalyticsDashboardResult,
) -> Dict[str, Any]:
    """Assemble the compact, path-free evidence payload from Modules 1-6 outputs."""
    meta = repository_metadata.model_dump(mode="json", exclude={"owner", "html_url"})
    meta["owner"] = repository_metadata.owner.login

    static = static_analysis_result.model_dump(
        mode="json",
        exclude={"local_path", "directory_tree", "marker_files", "ignored_directories", "scanned_at", "readme_content"},
    )
    tree = static_analysis_result.directory_tree
    static["top_level_entries"] = [
        {"name": c.name, "type": c.type} for c in (tree.children or [])[:_MAX_TOP_LEVEL_ENTRIES]
    ]
    static["language_distribution"] = static["language_distribution"][:_MAX_LANGUAGES]

    # The raw month-by-month commit timeline is deliberately excluded here:
    # for a sparse-history repository it is mostly zeros (see
    # CommitTimelineFormatter's docstring for the real example that
    # motivated this), adding many tokens for little signal. The summary
    # statistics already in `git_history` (total_commits, date range,
    # average cadence, activity level) carry the same information far more
    # efficiently for the model to reason over.
    history = git_history_result.model_dump(
        mode="json", exclude={"local_path", "analyzed_at", "monthly_commit_timeline"}
    )

    readme_available = static_analysis_result.marker_files.readme.present
    readme_content = static_analysis_result.readme_content
    readme_excerpt_truncated = static_analysis_result.readme_truncated
    if readme_content and len(readme_content) > _MAX_README_CHARS_FOR_PROMPT:
        readme_content = readme_content[:_MAX_README_CHARS_FOR_PROMPT]
        readme_excerpt_truncated = True

    not_provided = list(_ALWAYS_NOT_PROVIDED)
    if not readme_available or not readme_content:
        not_provided.insert(0, "README text")

    return {
        "repository_metadata": meta,
        "static_analysis": static,
        "git_history": history,
        "engineering_metrics": repository_metrics_result.model_dump(mode="json", exclude={"calculated_at"}),
        "analytics": {
            "health_gauge": analytics_result.health_gauge.model_dump(mode="json"),
            "overview_cards": [c.model_dump(mode="json") for c in analytics_result.overview_cards],
            "file_type_distribution": [
                f.model_dump(mode="json") for f in analytics_result.file_type_distribution[:_MAX_FILE_TYPES]
            ],
            "largest_directories": [
                {"name": d.name, "file_count": d.file_count} for d in analytics_result.largest_directories
            ],
        },
        "readme_available": readme_available,
        "readme_content": readme_content,
        "readme_excerpt_truncated": readme_excerpt_truncated,
        "not_provided": not_provided,
    }


def build_user_prompt(ai_input: Dict[str, Any]) -> str:
    """Render the user message: the evidence as JSON followed by the output specification.

    The evidence is serialized compactly (no indentation/pretty-printing).
    A model reads structural JSON correctly either way, so the whitespace
    `indent=2` would add is pure extra tokens for zero benefit - on a real
    sample repository, compact encoding alone cut prompt size by roughly a
    third.
    """
    compact_evidence = json.dumps(ai_input, separators=(",", ":"))
    return f"EVIDENCE (JSON):\n{compact_evidence}\n\n{OUTPUT_SPEC}"
