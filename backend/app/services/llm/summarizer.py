"""LLM Summarizer — natural language generation only.

The LLM is STRICTLY limited to summarization and explanation.
It NEVER:
- Decides risk scores (those come from the rule engine)
- Selects which chemicals are hazardous (determined by extraction pipeline)
- Makes safety recommendations (from knowledge base)
- Evaluates risk levels (from score calculator)

It ONLY:
- Generates human-readable summary text from structured data
- Rewrites technical information in plain language
- Provides natural language explanations of deterministic findings

Temperature is forced to 0. Response format is strict JSON Schema.
"""

from __future__ import annotations

from typing import Any

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.services.retry_handler import ai_retry

logger = structlog.get_logger(__name__)


# ── Pydantic output schemas ──────────────────────────────────────

class SummaryOutput(BaseModel):
    """Strict schema for LLM-generated executive summary."""

    summary_text: str = Field(
        ...,
        description="Natural language executive summary of the risk assessment",
        max_length=2000,
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="3-5 bullet points of the most important findings",
        max_length=5,
    )
    general_recommendation: str = Field(
        default="",
        description="One-sentence overall recommendation",
        max_length=500,
    )


class ExplanationOutput(BaseModel):
    """Strict schema for LLM-generated risk explanation."""

    explanation: str = Field(
        ...,
        description="Plain language explanation of why this chemical is risky",
        max_length=1000,
    )
    layperson_summary: str = Field(
        default="",
        description="One-sentence summary for non-scientists",
        max_length=300,
    )


# ── Summarizer ───────────────────────────────────────────────────

class LLMSummarizer:
    """Generate natural language text from deterministic report data.

    This is the ONLY place LLM is used in the report generation pipeline.
    All risk decisions have already been made by the rule engine.
    """

    SYSTEM_PROMPT = """You are a laboratory safety expert writing for researchers.
Your task is to generate clear, accurate natural language summaries from structured data.

CRITICAL RULES:
1. ONLY use the data provided to you. Do NOT invent or extrapolate.
2. Do NOT generate risk scores, risk levels, or safety classifications — these are already computed.
3. Write in professional but accessible English. The audience is lab researchers.
4. Be concise. Prefer short paragraphs and bullet points.
5. Always mention evidence sources when provided (NIOSH, OSHA, IARC, etc.).
6. Use Chinese (Simplified) for the summary text.
7. NEVER suggest that the assessment is uncertain unless explicitly told.
8. NEVER use phrases like "I think", "in my opinion", or "it might be".
"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self._client: AsyncOpenAI | None = None
        self._api_key = api_key or settings.openai_api_key
        self._base_url = base_url if base_url is not None else settings.openai_base_url
        self._model = model or settings.ai.model

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url or None,
                timeout=settings.ai.request_timeout,
                max_retries=0,  # Retry is handled by @ai_retry decorator
            )
        return self._client

    @ai_retry
    async def summarize(
        self,
        report_data: dict[str, Any],
        population: str = "pregnancy",
    ) -> SummaryOutput:
        """Generate executive summary from deterministic report data.

        Args:
            report_data: The full report dict (scores, chemicals, evidence)
            population: Target population for the summary

        Returns:
            SummaryOutput with natural language text.
        """
        # Build a structured prompt from deterministic data only
        prompt = self._build_summary_prompt(report_data, population)

        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,  # FORCED to 0 for determinism
                max_tokens=settings.ai.max_tokens_assessment,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                return self._fallback_summary(report_data)

            import json

            raw = json.loads(content)
            return SummaryOutput.model_validate(raw)

        except Exception as exc:
            logger.warning("llm_summary_failed", error=str(exc))
            return self._fallback_summary(report_data)

    @ai_retry
    async def explain_risk(
        self,
        chemical_name: str,
        risk_data: dict[str, Any],
        population: str = "pregnancy",
    ) -> ExplanationOutput:
        """Generate a plain-language explanation for a specific chemical risk.

        Args:
            chemical_name: Name of the chemical
            risk_data: Risk scores and evidence for this chemical
            population: Target population

        Returns:
            ExplanationOutput with natural language explanation.
        """
        prompt = f"""Explain the reproductive risk of {chemical_name} for {population}.

DATA (use ONLY this data):
- Risk scores: Pregnancy={risk_data.get('pregnancy_score',0)}, Fertility={risk_data.get('fertility_score',0)}, Lactation={risk_data.get('lactation_score',0)}
- Risk level: {risk_data.get('pregnancy_risk', 'Unknown')}
- Key hazards: {risk_data.get('evidence_notes', [])}
- CAS: {risk_data.get('cas_number', 'N/A')}
- Fired rules: {risk_data.get('fired_rule_names', [])}

Return JSON with:
- "explanation": detailed 2-3 sentence explanation in Chinese
- "layperson_summary": one sentence in simple language in Chinese"""

        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=800,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                return ExplanationOutput(
                    explanation=f"{chemical_name} has been identified as a {risk_data.get('pregnancy_risk', 'potential')} risk for {population}.",
                    layperson_summary=f"{chemical_name} may pose risks during {population}.",
                )

            import json

            raw = json.loads(content)
            return ExplanationOutput.model_validate(raw)

        except Exception as exc:
            logger.warning("llm_explanation_failed", chemical=chemical_name, error=str(exc))
            return ExplanationOutput(
                explanation=f"{chemical_name} has been identified as a {risk_data.get('pregnancy_risk', 'potential')} risk for {population} based on published toxicological data.",
                layperson_summary=f"{chemical_name} may pose risks during {population}. Consult your EHS officer.",
            )

    # ── Private helpers ──────────────────────────────────────────

    def _build_summary_prompt(
        self,
        report_data: dict[str, Any],
        population: str,
    ) -> str:
        """Build a structured summary prompt from deterministic report data."""
        overall = report_data.get("overall_risk", "Unknown")
        score = report_data.get("overall_score", 0)
        substances = report_data.get("identified_hazardous_materials", [])
        high_risk = report_data.get("executive_summary", {}).get("high_risk_count", 0)
        total = len(substances)

        chem_list = []
        for s in substances[:10]:  # Top 10
            name = s.get("substance_name", "Unknown")
            risk = s.get("pregnancy_risk", s.get("fertility_risk", "Unknown"))
            chem_list.append(f"  - {name}: {risk}")

        evidence_sources = set()
        for s in substances:
            for ev in s.get("evidence", []):
                evidence_sources.add(ev.get("source_organization", ""))

        return f"""Generate an executive summary for a laboratory safety report.

POPULATION: {population}
OVERALL RISK LEVEL: {overall}
OVERALL SCORE: {score}/100
TOTAL SUBSTANCES: {total}
HIGH RISK SUBSTANCES: {high_risk}

SUBSTANCES FOUND:
{chr(10).join(chem_list)}

EVIDENCE SOURCES: {', '.join(sorted(evidence_sources)) if evidence_sources else 'NIOSH, OSHA, PubChem'}

Return JSON with:
- "summary_text": 2-3 paragraph executive summary in Chinese
- "key_findings": 3-5 bullet point findings in Chinese
- "general_recommendation": one sentence recommendation in Chinese"""

    def _fallback_summary(self, report_data: dict[str, Any]) -> SummaryOutput:
        """Generate a fallback summary when LLM is unavailable."""
        overall = report_data.get("overall_risk", "Unknown")
        score = report_data.get("overall_score", 0)
        total = len(report_data.get("identified_hazardous_materials", []))
        high = report_data.get("executive_summary", {}).get("high_risk_count", 0)

        return SummaryOutput(
            summary_text=f"风险评估完成。总体风险等级：{overall}（评分：{score}/100）。"
            f"共识别 {total} 种化学物质，其中 {high} 种为高风险物质。"
            f"请仔细阅读详细报告并咨询您的机构EHS官员。",
            key_findings=[
                f"总体风险等级：{overall}",
                f"识别化学物质：{total} 种",
                f"高风险物质：{high} 种",
                "请参考详细报告获取完整风险信息",
            ],
            general_recommendation=f"基于 {total} 种化学物质的分析，建议{'严格遵循防护措施' if high > 0 else '保持标准实验室安全操作'}。",
        )


# Module-level singleton
_summarizer: LLMSummarizer | None = None


def get_llm_summarizer() -> LLMSummarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = LLMSummarizer()
    return _summarizer
