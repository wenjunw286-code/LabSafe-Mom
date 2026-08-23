"""LLM Extractor — last-resort chemical extraction using LLM.

Only called when dictionary + CAS + regex matching find insufficient chemicals.
Uses temperature=0 and strict JSON schema for maximum determinism.
"""

from __future__ import annotations

from typing import Any

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.services.retry_handler import ai_retry

logger = structlog.get_logger(__name__)


class ExtractedSubstance(BaseModel):
    """A single substance extracted by LLM."""

    name: str = Field(..., description="Chemical name as it appears in protocol", max_length=200)
    category: str = Field(default="unknown", description="Category", max_length=100)
    found_in_section: str = Field(
        default="",
        description="Exact text from the protocol where this substance was found",
        max_length=300,
    )


class LLMExtractionResult(BaseModel):
    """LLM extraction output."""

    substances: list[ExtractedSubstance] = Field(default_factory=list)


class LLMExtractor:
    """LLM-based chemical extraction (last resort only).

    Used ONLY when deterministic methods (dictionary, CAS, regex)
    fail to find sufficient chemicals in the protocol text.

    Temperature is forced to 0 for maximum determinism.
    """

    EXTRACTION_PROMPT = """You are a laboratory chemical safety expert.
Extract ALL chemical substances, reagents, dyes, solvents, antibodies,
enzymes, and biological agents from the protocol text below.

Include:
- Organic solvents (methanol, ethanol, acetone, xylene, chloroform, DMSO, etc.)
- Fixatives (formaldehyde, PFA, glutaraldehyde, osmium tetroxide, etc.)
- Dyes/stains (hematoxylin, eosin, DAB, DAPI, Coomassie, ethidium bromide, etc.)
- Antibiotics (penicillin, streptomycin, kanamycin, etc.)
- Buffers (Tris, HEPES, PBS, etc.) — only if hazardous
- Enzymes (trypsin, collagenase, proteinase K, etc.)
- Toxic reagents (phenol, chloroform, acrylamide, TEMED, etc.)
- Nanoparticles, radioactive isotopes, cytotoxic drugs
- Anesthetics (isoflurane, ketamine, etc.)

For each substance, provide:
- "name": exact name as found in the protocol
- "category": one of [solvent, fixative, dye, antibiotic, buffer, enzyme, reagent, anesthetic, biological, other]
- "found_in_section": the surrounding text (up to 200 chars)

Return JSON with a "substances" array.
Do NOT include common lab consumables (water, saline, PBS, tips, tubes)."""

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
                max_retries=0,
            )
        return self._client

    @ai_retry
    async def extract(self, text: str) -> list[dict[str, Any]]:
        """Extract chemicals from text using LLM.

        Args:
            text: Protocol text (truncated to 30000 chars).

        Returns:
            List of extracted substance dicts.
        """
        max_chars = 30000
        truncated = text[:max_chars]
        if len(text) > max_chars:
            truncated += "\n...[truncated]"

        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self.EXTRACTION_PROMPT},
                    {"role": "user", "content": f"Protocol text:\n{truncated}"},
                ],
                temperature=0,  # FORCED to 0
                max_tokens=settings.ai.max_tokens_extraction,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                return []

            import json

            raw = json.loads(content)
            validated = LLMExtractionResult.model_validate(raw)

            logger.info(
                "llm_extraction_complete",
                substances_found=len(validated.substances),
                names=[s.name for s in validated.substances],
            )
            return [
                {"name": s.name, "category": s.category, "found_in_section": s.found_in_section}
                for s in validated.substances
            ]

        except Exception as exc:
            logger.warning("llm_extraction_failed", error=str(exc))
            return []
