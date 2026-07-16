"""Knowledge Base Lookup — retrieve full toxicological profiles.

After chemicals are normalized to ChemicalIdentity records, this service
retrieves the complete toxicological profile for risk assessment.
Also falls back to the legacy hazardous_substances table for backward
compatibility.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chemical_kb import ChemicalIdentity, ChemicalSynonym, EvidenceCitation
from app.models.substance import HazardousSubstance

logger = structlog.get_logger(__name__)


RISK_SCORE_HINTS = {
    "critical": 85,
    "high": 70,
    "moderate": 45,
    "low": 15,
    "safe": 0,
    "acceptable": 5,
    "unknown": 20,
}

LEGACY_ALIASES = {
    "甲醛": "Formaldehyde",
    "formalin": "Formaldehyde",
    "福尔马林": "Formaldehyde",
    "多聚甲醛": "Paraformaldehyde",
    "甲醇": "Methanol",
    "乙醇": "Ethanol",
    "酒精": "Ethanol",
    "二甲基亚砜": "DMSO",
    "dmso": "DMSO",
    "叠氮化钠": "Sodium Azide",
    "吐温-20": "Tween-20",
    "tween-20": "Tween-20",
    "吐温20": "Tween-20",
    "pbs": "PBS",
    "磷酸盐缓冲液": "PBS",
    "氯化钠": "Sodium Chloride",
    "nacl": "Sodium Chloride",
    "醋酸铅": "Lead acetate",
    "乙酸铅": "Lead acetate",
    "lead acetate": "Lead acetate",
}

SUPPLEMENTAL_PROFILES: dict[str, dict[str, Any]] = {
    "301-04-2": {
        "id": "supplemental:301-04-2",
        "canonical_name_en": "Lead acetate",
        "canonical_name_zh": "醋酸铅",
        "cas_number": "301-04-2",
        "category": "Heavy metal salt",
        "pregnancy_risk": "Critical Risk",
        "fertility_risk": "Critical Risk",
        "lactation_risk": "High Risk",
        "ghs_classification": "Repr. 1A, Acute Tox. 4, STOT RE 2, Aquatic Chronic 1",
        "hazard_statements": "Lead compound; known developmental and reproductive toxicant",
        "effects_on_fetus": "Lead compounds cross the placenta and are associated with fetal neurodevelopmental toxicity and adverse pregnancy outcomes.",
        "effects_on_reproduction": "Lead exposure is associated with impaired fertility and germ cell toxicity.",
        "effects_on_breastfeeding": "Lead can be transferred to infants through maternal body burden and contaminated dust; strict exposure avoidance is recommended.",
        "recommended_ppe": "Certified fume hood or balance enclosure, double nitrile gloves, lab coat, safety goggles, dedicated weighing tools",
        "recommended_precautions": "Avoid pregnancy/lactation handling where possible; weigh powders in containment; prevent dust; use wet methods; segregate lead waste; perform surface decontamination.",
        "references": "OSHA Lead Standard 29 CFR 1910.1025; NIOSH reproductive health guidance; ECHA lead compound classifications",
        "reproductive_toxin": True,
        "teratogen": True,
        "mutagen": False,
        "carcinogen_class": "2A",
        "placental_transfer": True,
        "volatile": False,
        "dermal_absorption": True,
        "acute_toxicity_ld50": 466,
        "evidence_level": "A",
        "data_source": "supplemental_kb",
        "synonyms": ["Lead acetate", "lead(II) acetate", "醋酸铅", "乙酸铅"],
        "status": "FOUND_SUPPLEMENTAL",
    },
    "7647-14-5": {
        "id": "supplemental:7647-14-5",
        "canonical_name_en": "Sodium Chloride",
        "canonical_name_zh": "氯化钠",
        "cas_number": "7647-14-5",
        "category": "Buffer salt",
        "pregnancy_risk": "Safe",
        "fertility_risk": "Safe",
        "lactation_risk": "Safe",
        "ghs_classification": "Not classified as hazardous",
        "hazard_statements": "",
        "effects_on_fetus": "No specific reproductive hazard expected under normal laboratory buffer preparation conditions.",
        "effects_on_reproduction": "No specific fertility hazard expected.",
        "effects_on_breastfeeding": "No specific lactation hazard expected.",
        "recommended_ppe": "Standard laboratory PPE",
        "recommended_precautions": "Use normal good laboratory practice and avoid nuisance dust.",
        "references": "Common laboratory reagent; SDS not classified as hazardous",
        "reproductive_toxin": False,
        "teratogen": False,
        "mutagen": False,
        "carcinogen_class": None,
        "placental_transfer": False,
        "volatile": False,
        "dermal_absorption": False,
        "acute_toxicity_ld50": 3000,
        "evidence_level": "D",
        "data_source": "supplemental_kb",
        "synonyms": ["Sodium Chloride", "NaCl", "氯化钠"],
        "status": "FOUND_SUPPLEMENTAL",
    },
}

for _profile in list(SUPPLEMENTAL_PROFILES.values()):
    for _alias in _profile.get("synonyms", []):
        LEGACY_ALIASES.setdefault(_alias.lower(), _profile["canonical_name_en"])
        LEGACY_ALIASES.setdefault(_alias, _profile["canonical_name_en"])


class KnowledgeBaseLookup:
    """Retrieve full chemical profiles from the knowledge base.

    For each normalized chemical, fetches:
    - Toxicological properties (reproductive_toxin, teratogen, etc.)
    - Regulatory limits (OSHA PEL, NIOSH REL, etc.)
    - Safety controls (PPE, engineering controls)
    - Synonyms (for display)
    - Evidence citations (for report)

    Falls back to legacy hazardous_substances for backward compatibility.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def lookup(
        self,
        identity_id: int,
    ) -> dict[str, Any] | None:
        """Look up a single chemical by identity ID."""
        results = await self.lookup_batch([identity_id])
        return results[0] if results else None

    async def lookup_batch(
        self,
        identity_ids: list[int],
    ) -> list[dict[str, Any]]:
        """Look up multiple chemicals in a single query.

        Args:
            identity_ids: List of ChemicalIdentity IDs.

        Returns:
            List of chemical profile dicts.
        """
        if not identity_ids:
            return []

        # Run all 3 queries concurrently
        async def fetch_identities():
            stmt = select(ChemicalIdentity).where(
                ChemicalIdentity.id.in_(identity_ids)
            )
            result = await self._db.execute(stmt)
            return {ci.id: ci for ci in result.scalars().all()}

        async def fetch_synonyms():
            stmt = select(ChemicalSynonym).where(
                ChemicalSynonym.chemical_identity_id.in_(identity_ids)
            )
            result = await self._db.execute(stmt)
            syn_map: dict[int, list[str]] = {}
            for syn in result.scalars().all():
                syn_map.setdefault(syn.chemical_identity_id, []).append(syn.synonym)
            return syn_map

        async def fetch_evidence():
            stmt = select(EvidenceCitation).where(
                EvidenceCitation.chemical_identity_id.in_(identity_ids)
            )
            result = await self._db.execute(stmt)
            ev_map: dict[int, list[dict[str, Any]]] = {}
            for ev in result.scalars().all():
                ev_map.setdefault(ev.chemical_identity_id, []).append({
                    "claim": ev.claim,
                    "claim_domain": ev.claim_domain,
                    "source_organization": ev.source_organization,
                    "source_document": ev.source_document,
                    "evidence_strength": ev.evidence_strength,
                    "population": ev.population,
                })
            return ev_map

        identities, synonyms_by_id, evidence_by_id = await asyncio.gather(
            fetch_identities(), fetch_synonyms(), fetch_evidence()
        )

        # Build result profiles
        profiles: list[dict[str, Any]] = []
        for cid in identity_ids:
            ci = identities.get(cid)
            if ci is None:
                # Try legacy fallback
                legacy = await self._legacy_lookup(cid)
                if legacy:
                    profiles.append(legacy)
                else:
                    profiles.append({
                        "id": cid,
                        "canonical_name_en": "Unknown",
                        "status": "NOT_FOUND",
                    })
                continue

            profile = {
                "id": ci.id,
                "canonical_name_en": ci.canonical_name_en,
                "canonical_name_zh": ci.canonical_name_zh,
                "cas_number": ci.cas_number,
                "pubchem_cid": ci.pubchem_cid,
                "molecular_formula": ci.molecular_formula,
                "molecular_weight": ci.molecular_weight,
                # Toxicological
                "reproductive_toxin": ci.reproductive_toxin,
                "carcinogen_class": ci.carcinogen_class,
                "mutagen": ci.mutagen,
                "teratogen": ci.teratogen,
                "pregnancy_category": ci.pregnancy_category,
                "lactation_risk_category": ci.lactation_risk_category,
                "placental_transfer": ci.placental_transfer,
                "volatile": ci.volatile,
                "dermal_absorption": ci.dermal_absorption,
                "acute_toxicity_ld50": ci.acute_toxicity_ld50,
                # Regulatory
                "osha_pel": ci.osha_pel,
                "niosh_rel": ci.niosh_rel,
                "acgih_tlv": ci.acgih_tlv,
                "niosh_idlh": ci.niosh_idlh,
                # Safety
                "engineering_controls": ci.engineering_controls,
                "recommended_ppe": ci.recommended_ppe,
                "waste_disposal": ci.waste_disposal,
                "safer_alternatives": ci.safer_alternatives,
                # Metadata
                "data_source": ci.data_source,
                "evidence_level": ci.evidence_level,
                # Related
                "synonyms": synonyms_by_id.get(ci.id, []),
                "evidence": evidence_by_id.get(ci.id, []),
                "status": "FOUND",
            }
            profiles.append(profile)

        logger.info(
            "kb_lookup_complete",
            requested=len(identity_ids),
            found=len(identities),
            with_evidence=sum(1 for p in profiles if p.get("evidence")),
        )
        return profiles

    async def lookup_by_identifiers_batch(
        self,
        identifiers: list[dict[str, Any]],
    ) -> list[dict[str, Any] | None]:
        """Resolve chemicals by CAS/name against new, legacy, and supplemental KBs."""
        profiles: list[dict[str, Any] | None] = []
        for item in identifiers:
            cas = item.get("cas_number")
            names = [
                item.get("canonical_name_en"),
                item.get("canonical_name_zh"),
                item.get("raw_name"),
                item.get("substance_name"),
            ]
            profiles.append(await self.lookup_by_identifier(cas=cas, names=names))
        return profiles

    async def lookup_by_identifier(
        self,
        cas: str | None = None,
        names: list[str | None] | None = None,
    ) -> dict[str, Any] | None:
        """Resolve one chemical without requiring a ChemicalIdentity ID."""
        names = [n.strip() for n in (names or []) if n and n.strip()]
        if cas:
            direct = self._supplemental_lookup(cas)
            if direct:
                return direct

            stmt = select(HazardousSubstance).where(HazardousSubstance.cas_number == cas)
            result = await self._db.execute(stmt)
            legacy_matches = result.scalars().all()
            if legacy_matches:
                return self._legacy_profile(self._pick_best_legacy_match(legacy_matches), matched_by="legacy_cas")

        for name in names:
            direct = self._supplemental_lookup(name)
            if direct:
                return direct

            canonical_hint = LEGACY_ALIASES.get(name) or LEGACY_ALIASES.get(name.lower())
            search_terms = [name]
            if canonical_hint:
                search_terms.insert(0, canonical_hint)

            lowered_terms = [term.lower() for term in search_terms]
            exact_stmt = select(HazardousSubstance).where(
                func.lower(HazardousSubstance.chemical_name).in_(lowered_terms)
            )
            exact_result = await self._db.execute(exact_stmt)
            exact_matches = exact_result.scalars().all()
            if exact_matches:
                return self._legacy_profile(self._pick_best_legacy_match(exact_matches), matched_by="legacy_name_exact")

            partial_conditions = [
                func.lower(HazardousSubstance.chemical_name).like(f"%{term.lower()}%")
                for term in search_terms
                if len(term) >= 4
            ]
            if not partial_conditions:
                continue

            stmt = select(HazardousSubstance).where(or_(*partial_conditions))
            result = await self._db.execute(stmt)
            legacy_matches = result.scalars().all()
            if legacy_matches:
                return self._legacy_profile(self._pick_best_legacy_match(legacy_matches), matched_by="legacy_name")

        return None

    async def _legacy_lookup(self, identity_id: int) -> dict[str, Any] | None:
        """Fallback to legacy hazardous_substances table."""
        stmt = select(HazardousSubstance).where(
            HazardousSubstance.id == identity_id
        )
        result = await self._db.execute(stmt)
        hs = result.scalar_one_or_none()
        if hs is None:
            return None

        return self._legacy_profile(hs, matched_by="legacy_id")

    @staticmethod
    def _pick_best_legacy_match(matches: list[HazardousSubstance]) -> HazardousSubstance:
        """Prefer the strongest legacy risk entry when duplicate CAS rows exist."""
        if matches and matches[0].cas_number == "67-68-5":
            for hs in matches:
                if "dimethyl sulfoxide" in hs.chemical_name.lower():
                    return hs

        def rank(hs: HazardousSubstance) -> int:
            risks = [hs.pregnancy_risk, hs.fertility_risk, hs.lactation_risk]
            return max(_risk_score_hint(r) for r in risks)

        return sorted(matches, key=rank, reverse=True)[0]

    @staticmethod
    def _legacy_profile(hs: HazardousSubstance, matched_by: str) -> dict[str, Any]:
        risk_text = " ".join(
            str(x or "")
            for x in [
                hs.pregnancy_risk,
                hs.fertility_risk,
                hs.lactation_risk,
                hs.ghs_classification,
                hs.hazard_statements,
                hs.effects_on_fetus,
                hs.effects_on_reproduction,
                hs.references,
            ]
        ).lower()
        name_lower = hs.chemical_name.lower()

        return {
            "id": hs.id,
            "canonical_name_en": hs.chemical_name,
            "canonical_name_zh": hs.chemical_name,
            "cas_number": hs.cas_number,
            "category": hs.category,
            "pregnancy_risk": hs.pregnancy_risk,
            "fertility_risk": hs.fertility_risk,
            "lactation_risk": hs.lactation_risk,
            "reproductive_toxin": _is_reproductive_toxin(risk_text),
            "teratogen": _is_teratogen(risk_text),
            "mutagen": "mutagen" in risk_text or "h341" in risk_text or "h340" in risk_text,
            "carcinogen_class": _infer_carcinogen_class(risk_text),
            "pregnancy_category": None,
            "lactation_risk_category": _infer_lactation_category(hs.lactation_risk),
            "placental_transfer": _mentions_placental_transfer(risk_text),
            "volatile": _infer_volatility(name_lower, risk_text),
            "dermal_absorption": _infer_dermal_absorption(risk_text),
            "acute_toxicity_ld50": _infer_ld50(hs.chemical_name, hs.cas_number),
            "osha_pel": _extract_limit(hs.references, "OSHA PEL"),
            "niosh_rel": _extract_limit(hs.references, "NIOSH REL"),
            "acgih_tlv": _extract_limit(hs.references, "ACGIH TLV"),
            "niosh_idlh": _extract_limit(hs.references, "NIOSH IDLH"),
            "engineering_controls": _infer_engineering_controls(hs.recommended_precautions),
            "recommended_ppe": hs.recommended_ppe,
            "recommended_precautions": hs.recommended_precautions,
            "exposure_routes": hs.exposure_routes,
            "effects_on_fetus": hs.effects_on_fetus,
            "effects_on_reproduction": hs.effects_on_reproduction,
            "effects_on_breastfeeding": hs.effects_on_breastfeeding,
            "references": hs.references,
            "hazard_statements": hs.hazard_statements,
            "ghs_classification": hs.ghs_classification,
            "status": "FOUND_LEGACY",
            "evidence_level": "D",
            "data_source": "legacy_db",
            "matched_by": matched_by,
            "synonyms": _legacy_synonyms(hs),
            "evidence": [],
        }

    @staticmethod
    def _supplemental_lookup(identifier: str | None) -> dict[str, Any] | None:
        if not identifier:
            return None

        key = identifier.strip()
        lowered = key.lower()
        for cas, profile in SUPPLEMENTAL_PROFILES.items():
            names = [profile["canonical_name_en"], profile.get("canonical_name_zh"), *profile.get("synonyms", [])]
            if key == cas or lowered in [str(n).lower() for n in names if n]:
                return dict(profile)

        canonical_hint = LEGACY_ALIASES.get(key) or LEGACY_ALIASES.get(lowered)
        if canonical_hint:
            for profile in SUPPLEMENTAL_PROFILES.values():
                if profile["canonical_name_en"].lower() == canonical_hint.lower():
                    return dict(profile)
        return None


def _risk_score_hint(risk: str | None) -> int:
    risk_lower = str(risk or "unknown").lower()
    for token, score in RISK_SCORE_HINTS.items():
        if token in risk_lower:
            return score
    return 20


def _is_reproductive_toxin(text: str) -> bool:
    return any(token in text for token in ["reprotoxic", "repr", "reproductive", "fertility", "developmental", "fetus", "fetal", "teratogen", "h360", "h361"])


def _is_teratogen(text: str) -> bool:
    return any(token in text for token in ["teratogen", "developmental", "fetal", "fetus", "unborn child", "h360d", "h361d"])


def _mentions_placental_transfer(text: str) -> bool:
    return any(token in text for token in ["placenta", "placental", "cross the placenta"])


def _infer_carcinogen_class(text: str) -> str | None:
    if "alcoholic beverages" in text and "lab use considered low risk" in text:
        return None
    if "iarc group 1" in text or "group 1" in text or "carcinogen 1" in text:
        return "1"
    if "iarc group 2a" in text or "group 2a" in text:
        return "2A"
    if "iarc group 2b" in text or "group 2b" in text or "carc 2" in text:
        return "2B"
    return None


def _infer_lactation_category(risk: str | None) -> str | None:
    score = _risk_score_hint(risk)
    if score >= 70:
        return "Contraindicated"
    if score >= 60:
        return "Hold Feeding"
    return None


def _infer_volatility(name: str, text: str) -> bool:
    volatile_names = ["formaldehyde", "methanol", "ethanol", "acetone", "xylene", "toluene", "chloroform", "dichloromethane", "dmf", "acetonitrile", "hexane"]
    return any(token in name for token in volatile_names) or any(token in text for token in ["volatile", "vapor", "vapour", "ppm", "inhalation"])


def _infer_dermal_absorption(text: str) -> bool:
    return any(token in text for token in ["dermal", "skin", "h311", "skin absorption", "absorbed through skin"])


def _infer_ld50(name: str, cas: str | None) -> float | None:
    known = {
        "26628-22-8": 27.0,
        "50-00-0": 100.0,
        "67-56-1": 5628.0,
        "67-68-5": 14500.0,
        "64-17-5": 7060.0,
        "9005-64-5": 38000.0,
    }
    if cas in known:
        return known[cas]
    lower = name.lower()
    if "sodium azide" in lower:
        return 27.0
    return None


def _extract_limit(references: str | None, label: str) -> str | None:
    if not references or label.lower() not in references.lower():
        return None
    pattern = re.compile(rf"{re.escape(label)}\s*:\s*([^;]+)", re.IGNORECASE)
    match = pattern.search(references)
    return match.group(1).strip() if match else None


def _infer_engineering_controls(precautions: str | None) -> str | None:
    if not precautions:
        return None
    text = precautions.lower()
    if "fume" in text or "hood" in text:
        return "Chemical fume hood"
    return None


def _legacy_synonyms(hs: HazardousSubstance) -> list[str]:
    aliases = [alias for alias, canonical in LEGACY_ALIASES.items() if canonical.lower() in hs.chemical_name.lower()]
    return sorted({hs.chemical_name, *(aliases[:8])})
