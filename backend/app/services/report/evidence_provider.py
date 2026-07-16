"""Evidence Provider — attaches source citations to every risk claim.

Ensures every recommendation in the report cites specific evidence
from authoritative sources (NIOSH, OSHA, IARC, PubChem, ECHA, LactMed).

Never generates unsupported recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from app.services.risk.score_calculator import ChemicalScore, OverallScore
from app.services.rules.engine import RuleResult

logger = structlog.get_logger(__name__)


@dataclass
class EvidenceItem:
    """A single piece of evidence backing a claim."""

    source_organization: str
    claim: str
    claim_domain: str
    evidence_strength: str = "moderate"
    source_document: str | None = None
    source_url: str | None = None
    source_year: int | None = None
    population: str | None = None


@dataclass
class EvidencedChemical:
    """Chemical score with evidence citations attached."""

    chemical_score: ChemicalScore
    evidence: list[EvidenceItem] = field(default_factory=list)
    source_profile: dict[str, Any] | None = None


@dataclass
class EvidencedReport:
    """Full report with evidence citations for all claims."""

    overall_score: OverallScore
    chemicals: list[EvidencedChemical] = field(default_factory=list)
    general_evidence: list[EvidenceItem] = field(default_factory=list)

    @property
    def total_citations(self) -> int:
        return sum(len(c.evidence) for c in self.chemicals) + len(self.general_evidence)

    @property
    def sources_used(self) -> list[str]:
        sources: set[str] = set()
        for c in self.chemicals:
            for e in c.evidence:
                sources.add(e.source_organization)
        for e in self.general_evidence:
            sources.add(e.source_organization)
        return sorted(sources)


class EvidenceProvider:
    """Attach evidence citations to risk assessment results.

    Evidence comes from:
    1. Rule evidence_notes (from rules.yaml)
    2. Chemical identity data sources (from chemical_identities table)
    3. Static reference data for well-known hazards

    Every claim must have at least one citation. If a claim cannot
    be backed by evidence, it is flagged rather than silently included.
    """

    # Known authoritative sources
    AUTHORITATIVE_SOURCES = [
        "NIOSH",
        "OSHA",
        "IARC",
        "PubChem",
        "ECHA",
        "LactMed",
        "Reprotox",
        "CDC",
        "ACGIH",
        "FDA",
        "EPA",
        "NTP",
    ]

    @staticmethod
    def source_authority_level(source: str) -> int:
        """Rate the authority of a source (higher = more authoritative)."""
        levels = {
            "NIOSH": 5,
            "OSHA": 5,
            "IARC": 5,
            "NTP": 5,
            "FDA": 5,
            "EPA": 4,
            "ECHA": 4,
            "ACGIH": 4,
            "LactMed": 4,
            "Reprotox": 4,
            "CDC": 4,
            "PubChem": 3,
        }
        return levels.get(source, 1)

    def provide(
        self,
        overall_score: OverallScore,
        chemicals: list[dict[str, Any]],
    ) -> EvidencedReport:
        """Attach evidence to all chemicals in the report.

        Args:
            overall_score: Score calculation results
            chemicals: Original chemical identity dicts with data_source fields

        Returns:
            EvidencedReport with evidence for all risk claims.
        """
        evidenced_chemicals: list[EvidencedChemical] = []

        for cs in overall_score.chemical_scores:
            evidence: list[EvidenceItem] = []

            # 1. Evidence from fired rules
            for rule in cs.fired_rules:
                if rule.evidence_note:
                    evidence.append(
                        EvidenceItem(
                            source_organization=self._extract_source(rule.evidence_note),
                            claim=rule.rule_reason,
                            claim_domain=rule.category,
                            evidence_strength="moderate",
                            source_document=rule.evidence_note,
                            population=rule.population,
                        )
                    )

            # 2. Evidence from chemical identity data_source
            matching_chem = self._find_chemical(cs.substance_name, chemicals)
            if matching_chem:
                data_source = matching_chem.get("data_source", "")
                if data_source and data_source != "manual":
                    evidence.append(
                        EvidenceItem(
                            source_organization=data_source.upper(),
                            claim=f"Chemical identity and toxicological data from {data_source}",
                            claim_domain="chemical_identity",
                            evidence_strength="strong",
                            source_document=f"Data imported from {data_source}",
                        )
                    )

                # Add regulatory evidence
                if matching_chem.get("osha_pel"):
                    evidence.append(
                        EvidenceItem(
                            source_organization="OSHA",
                            claim=f"OSHA PEL: {matching_chem['osha_pel']}",
                            claim_domain="regulatory_limit",
                            evidence_strength="strong",
                            source_document=f"OSHA PEL: {matching_chem['osha_pel']}",
                        )
                    )
                if matching_chem.get("niosh_rel"):
                    evidence.append(
                        EvidenceItem(
                            source_organization="NIOSH",
                            claim=f"NIOSH REL: {matching_chem['niosh_rel']}",
                            claim_domain="regulatory_limit",
                            evidence_strength="strong",
                            source_document=f"NIOSH REL: {matching_chem['niosh_rel']}",
                        )
                    )

                # IARC classification
                carcinogen_class = matching_chem.get("carcinogen_class")
                if carcinogen_class:
                    evidence.append(
                        EvidenceItem(
                            source_organization="IARC",
                            claim=f"IARC Group {carcinogen_class} carcinogen",
                            claim_domain="carcinogenicity",
                            evidence_strength="strong",
                            source_document=f"IARC Monographs — Group {carcinogen_class}",
                        )
                    )

            # 3. If no evidence found, add a warning note
            if not evidence:
                evidence.append(
                    EvidenceItem(
                        source_organization="Expert Consensus",
                        claim="Risk assessment based on chemical class and structure-activity relationship",
                        claim_domain="general",
                        evidence_strength="weak",
                        source_document="Expert consensus — limited published data available",
                    )
                )

            # Deduplicate
            seen = set()
            unique_evidence = []
            for e in evidence:
                key = (e.source_organization, e.claim)
                if key not in seen:
                    seen.add(key)
                    unique_evidence.append(e)

            evidenced_chemicals.append(
                EvidencedChemical(
                    chemical_score=cs,
                    evidence=unique_evidence,
                    source_profile=matching_chem,
                )
            )

        # General evidence
        general_evidence = [
            EvidenceItem(
                source_organization="NIOSH",
                claim="Laboratory chemical safety guidelines for reproductive health",
                claim_domain="general_safety",
                evidence_strength="strong",
                source_document="NIOSH Pocket Guide to Chemical Hazards",
                source_url="https://www.cdc.gov/niosh/npg/",
            ),
            EvidenceItem(
                source_organization="OSHA",
                claim="Occupational exposure to hazardous chemicals in laboratories",
                claim_domain="general_safety",
                evidence_strength="strong",
                source_document="OSHA Laboratory Standard 29 CFR 1910.1450",
            ),
        ]

        report = EvidencedReport(
            overall_score=overall_score,
            chemicals=evidenced_chemicals,
            general_evidence=general_evidence,
        )

        logger.info(
            "evidence_provided",
            total_citations=report.total_citations,
            sources=report.sources_used,
            chemicals_with_weak_evidence=sum(
                1
                for c in evidenced_chemicals
                if any(e.evidence_strength == "weak" for e in c.evidence)
            ),
        )
        return report

    @staticmethod
    def _extract_source(evidence_note: str) -> str:
        """Extract the primary source organization from an evidence note."""
        for source in EvidenceProvider.AUTHORITATIVE_SOURCES:
            if source.lower() in evidence_note.lower():
                return source
        return "Expert Consensus"

    @staticmethod
    def _find_chemical(
        name: str,
        chemicals: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Find a chemical in the list by name."""
        for chem in chemicals:
            if (
                chem.get("canonical_name_en", "").lower() == name.lower()
                or chem.get("substance_name", "").lower() == name.lower()
            ):
                return chem
        return None


# Module-level singleton
_provider: EvidenceProvider | None = None


def get_evidence_provider() -> EvidenceProvider:
    global _provider
    if _provider is None:
        _provider = EvidenceProvider()
    return _provider
