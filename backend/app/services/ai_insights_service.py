"""
AI Layer service.

Turns the structured outputs of Modules 1-6 into structured AI insights via
Ollama. It performs no repository access, cloning, Git, static analysis or
metric calculation - it only builds a prompt from the evidence it is given,
asks the model, and validates the answer.

Failures raise `AIServiceError` subclasses; the Repository Orchestrator
decides how to represent them (as a structured partial result).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import ValidationError

from app.clients.ollama_client import OllamaClient
from app.core.exceptions import AIInvalidResponseError
from app.schemas.ai import AIInsightSection, AIInsights, AIInsightsResult, AIStatus
from app.schemas.analytics import AnalyticsDashboardResult
from app.schemas.git_history import GitHistoryResult
from app.schemas.metrics import RepositoryMetricsResult
from app.schemas.repository import RepositoryMetadata
from app.schemas.static_analysis import StaticAnalysisResult
from app.services.ai_prompt_builder import SECTION_KEYS, SYSTEM_PROMPT, build_ai_input, build_user_prompt

logger = logging.getLogger(__name__)


class AIInsightsService:
    """Generates structured, evidence-grounded insights from Modules 1-6 output."""

    def __init__(self, ollama_client: OllamaClient) -> None:
        self._client = ollama_client

    async def generate_insights(
        self,
        repository_metadata: RepositoryMetadata,
        static_analysis_result: StaticAnalysisResult,
        git_history_result: GitHistoryResult,
        repository_metrics_result: RepositoryMetricsResult,
        analytics_result: AnalyticsDashboardResult,
        advanced_visualizations: Optional[Dict[str, Any]] = None,
    ) -> AIInsightsResult:
        ai_input = build_ai_input(
            repository_metadata, static_analysis_result, git_history_result, repository_metrics_result, analytics_result
        )
        user_prompt = build_user_prompt(ai_input)
        raw_text = await self._client.chat_json(SYSTEM_PROMPT, user_prompt)
        insights: Optional[AIInsights] = None
        parse_error: Optional[AIInvalidResponseError] = None
        try:
            insights = self._parse(raw_text)
        except AIInvalidResponseError as exc:
            parse_error = exc

        missing_sections = [
            key for key in SECTION_KEYS
            if insights is None or not getattr(insights, key).available
        ]
        if parse_error is not None or missing_sections:
            # Small local models occasionally stop mid-JSON or omit sections.
            # Retry once with the same evidence instead of failing the entire AI tab.
            logger.warning(
                "[AI] Ollama response needs recovery (chars=%d, missing_sections=%s, parse_error=%s); retrying once.",
                len(raw_text or ""), missing_sections, parse_error,
            )
            retry_prompt = (
                user_prompt
                + "\n\nRETRY REQUIREMENT: Return one complete, syntactically valid JSON object. "
                  "Include all eight required top-level keys: " + ", ".join(SECTION_KEYS) + ". "
                  "Do not omit roadmap or README review sections. If README is absent, say so and suggest "
                  "repository-specific README sections. Keep strings concise, use empty arrays where appropriate, "
                  "do not use Markdown fences, and do not stop before the final brace."
            )
            retry_text = await self._client.chat_json(SYSTEM_PROMPT, retry_prompt)
            try:
                retry_insights = self._parse(retry_text)
                if insights is None:
                    insights = retry_insights
                else:
                    # Preserve valid first-pass sections; fill only the sections
                    # that the first response omitted or could not validate.
                    for key in missing_sections:
                        candidate = getattr(retry_insights, key)
                        if candidate.available:
                            setattr(insights, key, candidate)
            except AIInvalidResponseError:
                logger.exception(
                    "[AI] Ollama recovery attempt also failed (first_chars=%r, retry_chars=%d)",
                    (raw_text or "")[:240], len(retry_text or ""),
                )
                if insights is None:
                    raise

        if insights is None:
            raise AIInvalidResponseError("Ollama did not return any usable AI insight sections.")
        return AIInsightsResult(
            status=AIStatus.COMPLETED,
            model=self._client.model,
            generated_at=datetime.now(timezone.utc),
            insights=insights,
        )

    @staticmethod
    def _load_json_object(text: str) -> Dict[str, Any]:
        """Parse model output as a JSON object, tolerating code fences and surrounding prose."""
        candidate = text.strip()
        if candidate.startswith("```"):
            candidate = candidate.strip("`")
            candidate = candidate[4:] if candidate.lower().startswith("json") else candidate
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            start, end = candidate.find("{"), candidate.rfind("}")
            if start == -1 or end <= start:
                raise AIInvalidResponseError("The AI model did not return valid JSON.") from None
            try:
                parsed = json.loads(candidate[start : end + 1])
            except json.JSONDecodeError as exc:
                raise AIInvalidResponseError("The AI model did not return valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise AIInvalidResponseError("The AI model returned JSON that is not an object.")
        return parsed

    def _parse(self, text: str) -> AIInsights:
        raw = self._load_json_object(text)
        sections: Dict[str, AIInsightSection] = {}
        parsed_ok = 0
        for key in SECTION_KEYS:
            value: Optional[Any] = raw.get(key)
            if value is None:
                continue  # schema default marks it unavailable
            if isinstance(value, str):
                value = {"summary": value}
            try:
                sections[key] = AIInsightSection.model_validate(value)
                parsed_ok += 1
            except ValidationError:
                logger.warning("AI section '%s' could not be parsed; marking unavailable.", key)
                sections[key] = AIInsightSection(
                    available=False, missing_information=["This section could not be parsed from the model output."]
                )
        if parsed_ok == 0:
            raise AIInvalidResponseError("The AI model did not return any usable insight sections.")
        return AIInsights(**sections)
