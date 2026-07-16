"""Async risk matching service with DB lookup, batch matching, and AI fallback.

Uses `response_format={"type": "json_object"}` for broad LLM provider compatibility.
Priority order: DB exact → DB fuzzy → Cache → AI → Unknown fallback.
"""

from __future__ import annotations

import json

import structlog
from openai import AsyncOpenAI
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.substance import HazardousSubstance
from app.schemas.ai_models import RiskAssessment
from app.services.cache_service import ai_cache
from app.services.retry_handler import ai_retry

logger = structlog.get_logger(__name__)

# ── AI Fallback Prompt ────────────────────────────────────────
RISK_ASSESSMENT_SYSTEM_PROMPT = """You are a reproductive toxicology expert.
Assess the risk level of the given chemical substance for three populations:
pregnant (妊娠期), trying-to-conceive (备孕期), and breastfeeding (哺乳期) researchers.

You must respond with valid JSON only — no markdown, no code blocks, no explanatory text.

Format:
{
  "substance_name": "Name of the substance",
  "category": "Substance category",
  "pregnancy_risk": "Safe/Low Risk/Moderate Risk/High Risk/Unknown",
  "fertility_risk": "Safe/Low Risk/Moderate Risk/High Risk/Unknown",
  "lactation_risk": "Safe/Low Risk/Moderate Risk/High Risk/Unknown",
  "risk_reason": "Detailed rationale (Chinese, max 100 chars)",
  "effects_on_fetus": "Potential effects on fetal development (Chinese)",
  "effects_on_reproduction": "Potential effects on fertility (Chinese)",
  "effects_on_breastfeeding": "Potential effects on breastfeeding (Chinese)",
  "exposure_routes": ["吸入", "皮肤接触"],
  "recommended_ppe": "Recommended PPE (Chinese)",
  "recommended_precautions": "Precautions, each line starting with ✓ (Chinese)"
}

Risk definitions:
- Safe: No known risk under standard lab precautions
- Low Risk: Minor risk, standard PPE adequate
- Moderate Risk: Known risk, enhanced precautions needed
- High Risk: Known teratogen/reproductive toxin/milk-transferable; avoid or substitute
- Unknown: Insufficient data

Base on published toxicology data, NIOSH, GHS classifications.
If data insufficient, honestly report Unknown."""


class RiskMatcher:
    """Match extracted substances against local DB with async AI fallback.

    Features:
    - Non-blocking async database queries
    - Batch matching for efficiency
    - AI response caching (TTL-based)
    - Structured JSON output for reliable AI parsing
    - Graceful degradation on AI failure (returns Unknown)
    """

    def __init__(self) -> None:
        kwargs: dict = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        kwargs["timeout"] = settings.ai.request_timeout
        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.ai.model
        self._temperature = settings.ai.temperature
        self._max_tokens = settings.ai.max_tokens_assessment

    # ── Public API ────────────────────────────────────────────

    async def match(
        self,
        db: AsyncSession,
        substance_name: str,
        category: str = "其他",
        found_in_section: str = "",
    ) -> RiskAssessment:
        """Match a single substance against the risk database.

        Priority: DB exact → DB fuzzy → Cache → AI → Unknown fallback.
        """
        if not substance_name or not substance_name.strip():
            return self._unknown_result(substance_name, category, found_in_section)

        # 1. DB exact match
        db_result = await self._search_db_exact(db, substance_name)
        if db_result:
            logger.debug("risk_match_db_exact", substance=substance_name)
            return self._build_result(db_result.to_risk_dict(), found_in_section)

        # 2. DB fuzzy match
        db_result = await self._search_db_fuzzy(db, substance_name)
        if db_result:
            logger.debug("risk_match_db_fuzzy", substance=substance_name)
            return self._build_result(db_result.to_risk_dict(), found_in_section)

        # 3. AI cache
        cached = ai_cache.get(substance_name, category)
        if cached is not None:
            logger.debug("risk_match_cache_hit", substance=substance_name)
            return self._build_result(cached, found_in_section)

        # 4. AI fallback
        logger.info("risk_match_ai_fallback", substance=substance_name)
        ai_result = await self._ai_assess(substance_name, category)
        ai_cache.set(substance_name, category, ai_result)
        return self._build_result(ai_result, found_in_section)

    async def match_batch(
        self,
        db: AsyncSession,
        substances: list[dict],
    ) -> list[RiskAssessment]:
        """Match multiple substances concurrently."""
        import asyncio

        if not substances:
            return []

        logger.info("risk_match_batch_started", count=len(substances))
        tasks = [
            self.match(
                db,
                s.get("name", s.get("substance_name", "")),
                s.get("category", "其他"),
                s.get("found_in_section", ""),
            )
            for s in substances
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: list[RiskAssessment] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("risk_match_batch_item_failed", index=i, error=str(result))
                s = substances[i]
                name = s.get("name", s.get("substance_name", "unknown"))
                output.append(self._unknown_result(name, s.get("category", "其他"), s.get("found_in_section", "")))
            else:
                output.append(result)

        logger.info("risk_match_batch_completed", result_count=len(output))
        return output

    # ── DB Queries ────────────────────────────────────────────

    async def _search_db_exact(self, db: AsyncSession, name: str) -> HazardousSubstance | None:
        """Case-insensitive exact match on chemical_name."""
        result = await db.execute(
            select(HazardousSubstance).where(
                HazardousSubstance.chemical_name.ilike(name.strip())
            )
        )
        return result.scalar_one_or_none()

    async def _search_db_fuzzy(self, db: AsyncSession, name: str) -> HazardousSubstance | None:
        """Case-insensitive contains match on chemical_name."""
        trimmed = name.strip()
        parts = trimmed.split()
        conditions = [HazardousSubstance.chemical_name.ilike(f"%{trimmed}%")]
        if parts:
            conditions.append(HazardousSubstance.chemical_name.ilike(f"%{parts[0]}%"))
        result = await db.execute(
            select(HazardousSubstance).where(or_(*conditions))
        )
        return result.scalars().first()

    # ── AI Assessment ─────────────────────────────────────────

    @ai_retry
    async def _call_ai_assess(self, substance_name: str, category: str) -> RiskAssessment:
        """Make the structured output API call with retry."""
        user_prompt = (
            f"Substance: {substance_name}\n"
            f"Category: {category}\n\n"
            f"Assess the reproductive risk for pregnancy, fertility, and lactation."
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": RISK_ASSESSMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError(f"Empty AI response for {substance_name}")

        # Parse and validate
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Attempt markdown code block stripping
            cleaned = content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines)
            data = json.loads(cleaned)

        return RiskAssessment.model_validate(data)

    async def _ai_assess(self, substance_name: str, category: str) -> dict:
        """Call AI for risk assessment with graceful fallback."""
        try:
            result = await self._call_ai_assess(substance_name, category)
            result.substance_name = substance_name
            result.category = category
            result.from_database = False
            return result.model_dump()
        except Exception as exc:
            logger.error(
                "ai_assess_failed",
                substance=substance_name,
                error=str(exc),
                exc_info=True,
            )
            return {
                "substance_name": substance_name,
                "category": category,
                "pregnancy_risk": "Unknown",
                "fertility_risk": "Unknown",
                "lactation_risk": "Unknown",
                "risk_reason": "该物质不在本地数据库中，AI评估暂时不可用",
                "effects_on_fetus": "未知 — 数据不足",
                "effects_on_reproduction": "未知 — 数据不足",
                "effects_on_breastfeeding": "未知 — 数据不足",
                "exposure_routes": ["吸入", "皮肤接触"],
                "recommended_ppe": "建议使用标准实验室PPE，并在通风橱中操作",
                "recommended_precautions": "✓ 在通风橱中操作\n✓ 佩戴手套和实验服\n✓ 避免直接接触",
                "from_database": False,
                "found_in_section": "",
            }

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _build_result(data: dict, found_in_section: str = "") -> RiskAssessment:
        """Build a RiskAssessment from a dictionary, adding found_in_section."""
        data["found_in_section"] = found_in_section
        return RiskAssessment(**data)

    @staticmethod
    def _unknown_result(name: str, category: str, found_in_section: str = "") -> RiskAssessment:
        """Create an Unknown risk result."""
        return RiskAssessment(
            substance_name=name,
            category=category,
            pregnancy_risk="Unknown",
            fertility_risk="Unknown",
            lactation_risk="Unknown",
            risk_reason="数据不足，无法评估",
            found_in_section=found_in_section,
            from_database=False,
        )
