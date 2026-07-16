"""Hybrid Extraction Pipeline — orchestrates all extraction methods.

Runs dictionary matching, CAS number extraction, and regex pattern matching
concurrently. Merges and deduplicates results. Falls back to LLM extraction
only when coverage is insufficient.

This is the MAIN entry point for chemical extraction in v3.
Replaces the old ChemicalExtractor entirely.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.services.extraction.cas_matcher import CASMatch, CASMatcher
from app.services.extraction.dictionary_matcher import DictionaryMatch, DictionaryMatcher
from app.services.extraction.normalizer import ChemicalNormalizer, NormalizedChemical

logger = structlog.get_logger(__name__)


@dataclass
class ExtractionResult:
    """Complete extraction result with metadata."""

    chemicals: list[NormalizedChemical]
    total_raw_extractions: int
    resolved_count: int
    llm_fallback_used: bool = False
    extraction_methods_used: list[str] = field(default_factory=list)
    extraction_time_ms: float = 0.0


class HybridExtractionPipeline:
    """Orchestrate multi-method chemical extraction.

    Pipeline:
    1. Dictionary matching (fast, against chemical_synonyms)
    2. CAS number extraction (fast, regex + DB lookup)
    3. Merge & deduplicate
    4. Normalize all to ChemicalIdentity
    5. LLM fallback (only if coverage < threshold)

    Usage:
        pipeline = HybridExtractionPipeline(db_session)
        result = await pipeline.extract(protocol_text)
        for chem in result.chemicals:
            print(f"{chem.canonical_name_en} [{chem.cas_number}]")
    """

    # Minimum fraction of text to find chemicals in before falling back to LLM
    LLM_FALLBACK_THRESHOLD = 0.3  # If <30% of dictionary hits found

    # Minimum number of chemicals to find before skipping LLM
    MIN_CHEMICALS_WITHOUT_LLM = 2

    def __init__(self, db: AsyncSession):
        self._db = db
        # 注意：我们不再在 __init__ 中提前实例化 matcher，因为每个并发任务需要独立的会话
        # 只在 extract 中动态创建
        self._normalizer = ChemicalNormalizer(db)

    async def extract(self, text: str) -> ExtractionResult:
        """Run the full hybrid extraction pipeline.

        Args:
            text: Full protocol text.

        Returns:
            ExtractionResult with normalized chemicals and metadata.
        """
        t0 = time.monotonic()

        if not text or len(text.strip()) < 10:
            return ExtractionResult(
                chemicals=[],
                total_raw_extractions=0,
                resolved_count=0,
            )

        methods_used: list[str] = []

        # ── Step 1-2: Run matchers concurrently with independent sessions ──

        # 定义两个异步任务，每个使用自己独立的数据库会话
        async def run_dict():
            async with AsyncSessionLocal() as session:
                matcher = DictionaryMatcher(session)
                return await matcher.extract(text)

        async def run_cas():
            async with AsyncSessionLocal() as session:
                matcher = CASMatcher(session)
                return await matcher.extract(text)

        # 并发执行
        dict_task = asyncio.create_task(run_dict())
        cas_task = asyncio.create_task(run_cas())
        dict_matches, cas_matches = await asyncio.gather(dict_task, cas_task)

        if dict_matches:
            methods_used.append("dictionary")
        if cas_matches:
            methods_used.append("cas")

        # ── Step 3: Merge & deduplicate ──────────────────────────
        merged_names: list[str] = []

        # Add dictionary matches
        for m in dict_matches:
            merged_names.append(m.canonical_name_en)

        # Add CAS matches not already covered by dictionary
        dict_ids = {m.chemical_identity_id for m in dict_matches}
        for m in cas_matches:
            if m.chemical_identity_id and m.chemical_identity_id not in dict_ids:
                merged_names.append(m.canonical_name_en or m.raw_cas)
            elif not m.chemical_identity_id:
                # CAS found in text but not in DB — keep as-is
                merged_names.append(m.raw_cas)

        # Deduplicate
        merged_names = list(dict.fromkeys(merged_names))

        # ── Step 4: Normalize ────────────────────────────────────
        # 这里使用 self._db 的会话（串行，无并发问题）
        normalized = await self._normalizer.normalize_batch(merged_names)

        # ── Step 5: LLM fallback decision ────────────────────────
        llm_used = False
        resolved_count = sum(1 for n in normalized if n.status == "RESOLVED")

        needs_llm = (
            len(normalized) < self.MIN_CHEMICALS_WITHOUT_LLM
            or (
                len(text) > 500
                and len(normalized) == 0
            )
        )

        if needs_llm:
            logger.info("llm_fallback_triggered", reason="insufficient_coverage")
            try:
                from app.services.extraction.llm_extractor import LLMExtractor

                llm_extractor = LLMExtractor()
                llm_results = await llm_extractor.extract(text)
                if llm_results:
                    llm_names = [r.get("name", "") for r in llm_results if r.get("name")]
                    llm_normalized = await self._normalizer.normalize_batch(llm_names)
                    # Merge — LLM results supplement, don't replace
                    existing_names = {n.raw_name.lower() for n in normalized}
                    for ln in llm_normalized:
                        if ln.raw_name.lower() not in existing_names:
                            normalized.append(ln)
                            existing_names.add(ln.raw_name.lower())
                    llm_used = True
                    methods_used.append("llm_fallback")
            except Exception as exc:
                logger.warning("llm_fallback_failed", error=str(exc))

        resolved_count = sum(1 for n in normalized if n.status == "RESOLVED")

        result = ExtractionResult(
            chemicals=normalized,
            total_raw_extractions=len(merged_names),
            resolved_count=resolved_count,
            llm_fallback_used=llm_used,
            extraction_methods_used=methods_used,
            extraction_time_ms=(time.monotonic() - t0) * 1000,
        )

        logger.info(
            "extraction_complete",
            total=len(normalized),
            resolved=resolved_count,
            methods=methods_used,
            llm_fallback=llm_used,
            time_ms=round(result.extraction_time_ms, 1),
        )
        return result

    async def extract_names_only(self, text: str) -> list[str]:
        """Extract and return only canonical chemical names."""
        result = await self.extract(text)
        return [
            c.canonical_name_en or c.raw_name
            for c in result.chemicals
        ]
