"""CAS Number Matcher — extract CAS registry numbers from text.

Uses regex: \\b\\d{1,7}-\\d{2}-\\d\\b to find CAS numbers,
then looks them up in the chemical_identities table.

CAS format: up to 7 digits, hyphen, 2 digits, hyphen, 1 check digit.
Examples: 50-00-0 (formaldehyde), 67-56-1 (methanol), 7732-18-5 (water)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chemical_kb import ChemicalIdentity

logger = structlog.get_logger(__name__)

# CAS Registry Number regex: group1 (1-7 digits), group2 (2 digits), group3 (1 digit)
# Also validates the check digit sum
CAS_REGEX = re.compile(r"\b(\d{1,7})-(\d{2})-(\d)\b")

# Exclude patterns that look like CAS but aren't
NOT_CAS_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # Date: 2024-01-01
    re.compile(r"\b\d+-\d+-\d{4}\b"),  # Other date formats
    re.compile(r"\b\d+-\d+-\d+[a-zA-Z]\b"),  # Has trailing letter
]


@dataclass
class CASMatch:
    """A chemical matched by CAS number."""

    raw_cas: str  # e.g., "50-00-0"
    chemical_identity_id: int | None = None
    canonical_name_en: str | None = None
    canonical_name_zh: str | None = None
    cas_number: str | None = None
    pubchem_cid: int | None = None
    match_method: str = "cas_exact"
    found_in_section: str = ""


class CASMatcher:
    """Extract CAS numbers from text and look them up in the database.

    Usage:
        matcher = CASMatcher(db_session)
        matches = await matcher.extract(protocol_text)
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def extract(self, text: str) -> list[CASMatch]:
        """Find all CAS numbers in text and look them up.

        Args:
            text: Protocol text to scan.

        Returns:
            List of CASMatch results, deduplicated by CAS number.
        """
        if not text:
            return []

        # Find all CAS-like patterns
        raw_matches = CAS_REGEX.findall(text)
        if not raw_matches:
            return []

        # Reconstruct CAS strings: ("50", "00", "0") → "50-00-0"
        cas_candidates: list[str] = []
        for groups in raw_matches:
            cas = f"{groups[0]}-{groups[1]}-{groups[2]}"

            # Filter out non-CAS patterns
            is_valid = True
            for pattern in NOT_CAS_PATTERNS:
                if pattern.match(cas):
                    is_valid = False
                    break

            # Validate check digit (basic)
            if is_valid and self._validate_cas(cas):
                cas_candidates.append(cas)

        if not cas_candidates:
            return []

        # Deduplicate
        unique_cas = list(set(cas_candidates))

        # Look up in database
        stmt = select(ChemicalIdentity).where(
            ChemicalIdentity.cas_number.in_(unique_cas)
        )
        result = await self._db.execute(stmt)
        identities = {ci.cas_number: ci for ci in result.scalars().all()}

        # Build results
        matches: list[CASMatch] = []
        for cas in unique_cas:
            identity = identities.get(cas)
            # Find context in text
            idx = text.find(cas)
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(text), idx + len(cas) + 80)
                context = text[start:end].strip()
            else:
                context = ""

            match = CASMatch(
                raw_cas=cas,
                found_in_section=context,
            )

            if identity:
                match.chemical_identity_id = identity.id
                match.canonical_name_en = identity.canonical_name_en
                match.canonical_name_zh = identity.canonical_name_zh
                match.cas_number = identity.cas_number
                match.pubchem_cid = identity.pubchem_cid
            else:
                # CAS found in text but not in DB — still report it
                match.cas_number = cas

            matches.append(match)

        logger.info(
            "cas_matches",
            candidates=len(cas_candidates),
            db_matches=len(identities),
            unmatched=sum(1 for m in matches if m.chemical_identity_id is None),
        )
        return matches

    @staticmethod
    def _validate_cas(cas: str) -> bool:
        """Validate CAS check digit.

        CAS format: N₁...Nₖ-RR-C
        Check: (Nₖ×1 + Nₖ₋₁×2 + ... + N₁×k) mod 10 == C
        """
        try:
            parts = cas.split("-")
            if len(parts) != 3:
                return False
            digits_str = parts[0] + parts[1]
            check_digit = int(parts[2])
            digits = [int(d) for d in digits_str]
            digits.reverse()
            total = sum(d * (i + 1) for i, d in enumerate(digits))
            return total % 10 == check_digit
        except (ValueError, IndexError):
            return False
