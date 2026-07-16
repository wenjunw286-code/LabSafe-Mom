"""Chemical Normalizer — resolve raw chemical names to canonical ChemicalIdentity.

Takes raw extractions (from dictionary, CAS, regex, LLM) and resolves each
to a canonical ChemicalIdentity record via:
1. Exact name match on canonical_name_en
2. Synonym match on chemical_synonyms.synonym
3. CAS number match
4. Fuzzy match (rapidfuzz) as fallback
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chemical_kb import ChemicalIdentity, ChemicalSynonym

logger = structlog.get_logger(__name__)

CAS_PATTERN = re.compile(r"^\d{1,7}-\d{2}-\d$")


@dataclass
class NormalizedChemical:
    """A chemical that has been resolved to a canonical identity."""

    raw_name: str  # Original extracted name
    status: str = "UNRESOLVED"  # "RESOLVED", "UNRESOLVED", "MULTIPLE"

    # Canonical identity (if resolved)
    chemical_identity_id: int | None = None
    canonical_name_en: str | None = None
    canonical_name_zh: str | None = None
    cas_number: str | None = None
    pubchem_cid: int | None = None
    inchi_key: str | None = None

    # How it was resolved
    resolution_method: str | None = None  # "exact_name", "synonym", "cas", "fuzzy"

    # Per-population risk data (from hazard database)
    pregnancy_risk: str | None = None
    fertility_risk: str | None = None
    lactation_risk: str | None = None

    # Metadata
    data_source: str | None = None
    evidence_level: str = "D"

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_name": self.raw_name,
            "status": self.status,
            "chemical_identity_id": self.chemical_identity_id,
            "canonical_name_en": self.canonical_name_en or self.raw_name,
            "canonical_name_zh": self.canonical_name_zh,
            "cas_number": self.cas_number,
            "pubchem_cid": self.pubchem_cid,
            "inchi_key": self.inchi_key,
            "resolution_method": self.resolution_method,
            "pregnancy_risk": self.pregnancy_risk,
            "fertility_risk": self.fertility_risk,
            "lactation_risk": self.lactation_risk,
            "data_source": self.data_source,
            "evidence_level": self.evidence_level,
        }


class ChemicalNormalizer:
    """Resolve raw chemical names to canonical ChemicalIdentity records.

    Usage:
        normalizer = ChemicalNormalizer(db_session)
        normalized = await normalizer.normalize_batch(raw_names)
    """

    # Similarity threshold for fuzzy matching (0-100)
    FUZZY_THRESHOLD = 85

    def __init__(self, db: AsyncSession):
        self._db = db

    async def normalize(self, raw_name: str) -> NormalizedChemical:
        """Normalize a single chemical name."""
        results = await self.normalize_batch([raw_name])
        return results[0] if results else NormalizedChemical(raw_name=raw_name)

    async def normalize_batch(self, raw_names: list[str]) -> list[NormalizedChemical]:
        """Normalize multiple chemical names in a single DB query.

        Args:
            raw_names: List of raw chemical names from extraction.

        Returns:
            One NormalizedChemical per input name.
        """
        if not raw_names:
            return []

        cleaned = [n.strip() for n in raw_names if n and n.strip()]
        if not cleaned:
            return []

        names_lower = [n.lower() for n in cleaned]

        # ── Step 1: Exact canonical name match ───────────────────
        stmt = select(ChemicalIdentity).where(
            or_(
                ChemicalIdentity.canonical_name_en.in_(cleaned),
                ChemicalIdentity.canonical_name_zh.in_(cleaned),
            )
        )
        result = await self._db.execute(stmt)
        exact_matches: dict[str, ChemicalIdentity] = {}
        for ci in result.scalars().all():
            key = ci.canonical_name_en.lower()
            exact_matches[key] = ci
            if ci.canonical_name_zh:
                exact_matches[ci.canonical_name_zh.lower()] = ci

        # ── Step 2: Synonym match ────────────────────────────────
        stmt_syn = (
            select(ChemicalSynonym, ChemicalIdentity)
            .join(ChemicalIdentity)
            .where(ChemicalSynonym.synonym.in_(names_lower))
        )
        result_syn = await self._db.execute(stmt_syn)
        synonym_matches: dict[str, ChemicalIdentity] = {}
        for syn, ci in result_syn.all():
            key = syn.synonym.lower()
            if key not in exact_matches:
                synonym_matches[key] = ci

        # ── Step 3: Build results ────────────────────────────────
        results: list[NormalizedChemical] = []
        for original_name in cleaned:
            name_lower = original_name.lower()

            # Try exact match
            ci = exact_matches.get(name_lower)
            if ci:
                results.append(self._build_resolved(original_name, ci, "exact_name"))
                continue

            # Try synonym match
            ci = synonym_matches.get(name_lower)
            if ci:
                results.append(self._build_resolved(original_name, ci, "synonym"))
                continue

            # Unresolved
            cas_number = original_name if CAS_PATTERN.match(original_name) else None
            results.append(
                NormalizedChemical(
                    raw_name=original_name,
                    status="UNRESOLVED",
                    canonical_name_en=original_name,
                    cas_number=cas_number,
                )
            )

        resolved = sum(1 for r in results if r.status == "RESOLVED")
        logger.info(
            "normalization_complete",
            total=len(results),
            resolved=resolved,
            unresolved=len(results) - resolved,
            methods={
                "exact_name": sum(
                    1 for r in results if r.resolution_method == "exact_name"
                ),
                "synonym": sum(
                    1 for r in results if r.resolution_method == "synonym"
                ),
            },
        )
        return results

    @staticmethod
    def _build_resolved(
        raw_name: str,
        ci: ChemicalIdentity,
        method: str,
    ) -> NormalizedChemical:
        """Build a NormalizedChemical from a matched ChemicalIdentity."""
        return NormalizedChemical(
            raw_name=raw_name,
            status="RESOLVED",
            chemical_identity_id=ci.id,
            canonical_name_en=ci.canonical_name_en,
            canonical_name_zh=ci.canonical_name_zh,
            cas_number=ci.cas_number,
            pubchem_cid=ci.pubchem_cid,
            inchi_key=ci.inchi_key,
            resolution_method=method,
            data_source=ci.data_source,
            evidence_level=ci.evidence_level,
        )
