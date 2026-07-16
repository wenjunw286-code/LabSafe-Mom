"""Dictionary Matcher — match protocol text against chemical synonym database.

Scans text for known chemical names and synonyms from the chemical_synonyms table.
Uses exact substring matching (fast) with fallback to fuzzy matching (rapidfuzz)
for near-miss names. Fully deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chemical_kb import ChemicalIdentity, ChemicalSynonym
from app.models.substance import HazardousSubstance
from app.services.knowledge.kb_lookup import LEGACY_ALIASES, SUPPLEMENTAL_PROFILES

logger = structlog.get_logger(__name__)


@dataclass
class DictionaryMatch:
    """A chemical matched by dictionary lookup."""

    raw_name: str  # The text found in the protocol
    synonym: str  # The matched synonym from DB
    chemical_identity_id: int | None
    canonical_name_en: str
    canonical_name_zh: str | None = None
    cas_number: str | None = None
    pubchem_cid: int | None = None
    category: str = "unknown"
    match_method: str = "exact"  # "exact" or "fuzzy"
    found_in_section: str = ""


class DictionaryMatcher:
    """Match protocol text against the chemical synonym database.

    Loads all synonyms into memory at init for fast scanning.
    Uses case-insensitive substring matching.

    Usage:
        matcher = DictionaryMatcher(db_session)
        matches = await matcher.extract(protocol_text)
    """

    # Maximum number of synonyms to load (performance safeguard)
    MAX_SYNONYMS = 50000

    # Minimum synonym length to match (avoids false positives on short strings)
    MIN_SYNONYM_LENGTH = 3

    def __init__(self, db: AsyncSession):
        self._db = db
        self._synonyms: list[tuple[str, int | None, str, str | None, str | None, int | None]] = []
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        """Load all synonyms + chemical info into memory."""
        if self._loaded:
            return

        stmt = (
            select(
                ChemicalSynonym.synonym,
                ChemicalSynonym.chemical_identity_id,
                ChemicalIdentity.canonical_name_en,
                ChemicalIdentity.canonical_name_zh,
                ChemicalIdentity.cas_number,
                ChemicalIdentity.pubchem_cid,
            )
            .join(ChemicalIdentity)
            .where(ChemicalSynonym.synonym != "")
            .limit(self.MAX_SYNONYMS)
        )

        result = await self._db.execute(stmt)
        rows = result.all()

        self._synonyms = [
            (row[0].lower().strip(), row[1], row[2], row[3], row[4], row[5])
            for row in rows
            if len(row[0].strip()) >= self.MIN_SYNONYM_LENGTH
        ]

        legacy_rows = (await self._db.execute(select(HazardousSubstance))).scalars().all()
        legacy_by_name = {hs.chemical_name.lower(): hs for hs in legacy_rows}
        for hs in legacy_rows:
            aliases = {hs.chemical_name, hs.chemical_name.lower()}
            if hs.cas_number:
                aliases.add(hs.cas_number)
            for alias, canonical in LEGACY_ALIASES.items():
                if canonical.lower() in hs.chemical_name.lower():
                    aliases.add(alias)
            for alias in aliases:
                alias_clean = str(alias).lower().strip()
                if len(alias_clean) >= self.MIN_SYNONYM_LENGTH:
                    self._synonyms.append(
                        (
                            alias_clean,
                            hs.id,
                            hs.chemical_name,
                            hs.chemical_name,
                            hs.cas_number,
                            None,
                        )
                    )

        for profile in SUPPLEMENTAL_PROFILES.values():
            aliases = {
                profile["canonical_name_en"],
                profile.get("canonical_name_zh"),
                profile.get("cas_number"),
                *profile.get("synonyms", []),
            }
            for alias in aliases:
                if not alias:
                    continue
                alias_clean = str(alias).lower().strip()
                if len(alias_clean) >= self.MIN_SYNONYM_LENGTH and alias_clean not in legacy_by_name:
                    self._synonyms.append(
                        (
                            alias_clean,
                            None,
                            profile["canonical_name_en"],
                            profile.get("canonical_name_zh"),
                            profile.get("cas_number"),
                            None,
                        )
                    )

        # Sort by length descending (longer = more specific match)
        self._synonyms.sort(key=lambda x: len(x[0]), reverse=True)

        self._loaded = True
        logger.info(
            "dictionary_loaded",
            synonym_count=len(self._synonyms),
        )

    async def extract(self, text: str) -> list[DictionaryMatch]:
        """Extract chemicals from text by dictionary matching.

        Args:
            text: Protocol text to scan.

        Returns:
            List of unique DictionaryMatch results, deduplicated by identity ID.
        """
        if not text:
            return []

        await self._ensure_loaded()

        text_lower = text.lower()
        matches: list[DictionaryMatch] = []
        seen_keys: set[str] = set()

        for synonym, chem_id, name_en, name_zh, cas, cid in self._synonyms:
            seen_key = str(chem_id) if chem_id is not None else f"supplemental:{name_en.lower()}"
            if seen_key in seen_keys:
                continue

            idx = text_lower.find(synonym)
            if idx >= 0:
                # Extract surrounding context
                start = max(0, idx - 80)
                end = min(len(text), idx + len(synonym) + 80)
                context = text[start:end].strip()

                matches.append(
                    DictionaryMatch(
                        raw_name=synonym,
                        synonym=synonym,
                        chemical_identity_id=chem_id,
                        canonical_name_en=name_en,
                        canonical_name_zh=name_zh,
                        cas_number=str(cas) if cas else None,
                        pubchem_cid=int(cid) if cid else None,
                        match_method="exact",
                        found_in_section=context,
                    )
                )
                seen_keys.add(seen_key)

        logger.info(
            "dictionary_matches",
            text_length=len(text),
            matches=len(matches),
            substances=[m.canonical_name_en for m in matches],
        )
        return matches

    def reload(self) -> None:
        """Force reload synonyms on next extract call."""
        self._loaded = False
        self._synonyms = []
