"""Chemical Knowledge Base ORM models — SQLAlchemy 2.0 style.

Provides the canonical chemical registry (ChemicalIdentity), synonym lookup
(ChemicalSynonym), and evidence citations (EvidenceCitation) that back the
deterministic rule engine and evidence-based recommendations.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ChemicalIdentity(Base):
    """Canonical chemical registry — the single source of truth.

    Each row represents one unique chemical substance identified by
    InChIKey (gold standard), CAS number, and PubChem CID.
    All toxicological, regulatory, and safety data is denormalized here
    for fast deterministic lookups at analysis runtime.
    """

    __tablename__ = "chemical_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Identity ─────────────────────────────────────────────────
    canonical_name_en: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True
    )
    canonical_name_zh: Mapped[str | None] = mapped_column(String(500), default=None)
    cas_number: Mapped[str | None] = mapped_column(String(50), index=True, default=None)
    pubchem_cid: Mapped[int | None] = mapped_column(Integer, index=True, default=None)
    chebi_id: Mapped[int | None] = mapped_column(Integer, default=None)
    mesh_id: Mapped[str | None] = mapped_column(String(50), default=None)
    molecular_formula: Mapped[str | None] = mapped_column(String(100), default=None)
    molecular_weight: Mapped[float | None] = mapped_column(Float, default=None)
    smiles: Mapped[str | None] = mapped_column(Text, default=None)
    inchi: Mapped[str | None] = mapped_column(Text, default=None)
    inchi_key: Mapped[str | None] = mapped_column(String(30), index=True, default=None)
    iupac_name: Mapped[str | None] = mapped_column(Text, default=None)

    # ── Toxicological Properties ─────────────────────────────────
    reproductive_toxin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    carcinogen_class: Mapped[str | None] = mapped_column(
        String(10), default=None
    )  # "1", "2A", "2B", "3" (IARC)
    mutagen: Mapped[bool] = mapped_column(Boolean, default=False)
    teratogen: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    pregnancy_category: Mapped[str | None] = mapped_column(
        String(10), default=None
    )  # FDA: A/B/C/D/X or AU TGA category
    lactation_risk_category: Mapped[str | None] = mapped_column(
        String(20), default=None
    )  # LactMed: "Compatible", "Hold Feeding", "Contraindicated"
    placental_transfer: Mapped[bool | None] = mapped_column(Boolean, default=None)
    volatile: Mapped[bool | None] = mapped_column(Boolean, default=None)
    dermal_absorption: Mapped[bool | None] = mapped_column(Boolean, default=None)
    acute_toxicity_ld50: Mapped[float | None] = mapped_column(
        Float, default=None
    )  # mg/kg, oral-rat
    chronic_toxicity: Mapped[str | None] = mapped_column(Text, default=None)

    # ── Regulatory Limits ────────────────────────────────────────
    osha_pel: Mapped[str | None] = mapped_column(String(100), default=None)
    niosh_rel: Mapped[str | None] = mapped_column(String(100), default=None)
    acgih_tlv: Mapped[str | None] = mapped_column(String(100), default=None)
    niosh_idlh: Mapped[str | None] = mapped_column(String(100), default=None)

    # ── Safety Controls ──────────────────────────────────────────
    engineering_controls: Mapped[str | None] = mapped_column(Text, default=None)
    recommended_ppe: Mapped[str | None] = mapped_column(Text, default=None)
    waste_disposal: Mapped[str | None] = mapped_column(Text, default=None)
    safer_alternatives: Mapped[str | None] = mapped_column(Text, default=None)

    # ── Metadata ─────────────────────────────────────────────────
    data_source: Mapped[str] = mapped_column(
        String(100), default="manual"
    )  # "pubchem", "niosh", "echa", "manual"
    evidence_level: Mapped[str] = mapped_column(
        String(1), default="D"
    )  # A=human, B=animal, C=in-vitro, D=expert-consensus
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    synonyms: Mapped[list["ChemicalSynonym"]] = relationship(
        "ChemicalSynonym", back_populates="chemical", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["EvidenceCitation"]] = relationship(
        "EvidenceCitation", back_populates="chemical", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Serialize to dict for API responses."""
        return {
            "id": self.id,
            "canonical_name_en": self.canonical_name_en,
            "canonical_name_zh": self.canonical_name_zh,
            "cas_number": self.cas_number,
            "pubchem_cid": self.pubchem_cid,
            "molecular_formula": self.molecular_formula,
            "reproductive_toxin": self.reproductive_toxin,
            "carcinogen_class": self.carcinogen_class,
            "mutagen": self.mutagen,
            "teratogen": self.teratogen,
            "pregnancy_category": self.pregnancy_category,
            "lactation_risk_category": self.lactation_risk_category,
            "placental_transfer": self.placental_transfer,
            "volatile": self.volatile,
            "dermal_absorption": self.dermal_absorption,
            "osha_pel": self.osha_pel,
            "niosh_rel": self.niosh_rel,
            "acgih_tlv": self.acgih_tlv,
            "evidence_level": self.evidence_level,
        }


class ChemicalSynonym(Base):
    """All known names/synonyms for a chemical, with source tracking.

    Supports multilingual lookup (en, zh, ja, etc.) and tracks
    which external database provided each synonym.
    """

    __tablename__ = "chemical_synonyms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chemical_identity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chemical_identities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    synonym: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(
        String(10), default="en"
    )  # "en", "zh", "ja", etc.
    source: Mapped[str] = mapped_column(
        String(50), default="manual"
    )  # "pubchem", "chebi", "mesh", "local_db"
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    chemical: Mapped["ChemicalIdentity"] = relationship(
        "ChemicalIdentity", back_populates="synonyms"
    )


class EvidenceCitation(Base):
    """Evidence backing every risk recommendation.

    Every claim about a chemical's hazard must be traceable to a
    specific authoritative source (NIOSH, OSHA, IARC, PubChem, etc.).
    """

    __tablename__ = "evidence_citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chemical_identity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chemical_identities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    claim_domain: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "reproductive_toxicity", "carcinogenicity", "mutagenicity", "teratogenicity"
    source_organization: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # "NIOSH", "OSHA", "IARC", "PubChem", "ECHA", "LactMed", "Reprotox"
    source_document: Mapped[str | None] = mapped_column(Text, default=None)
    source_url: Mapped[str | None] = mapped_column(Text, default=None)
    source_year: Mapped[int | None] = mapped_column(Integer, default=None)
    evidence_strength: Mapped[str] = mapped_column(
        String(20), default="moderate"
    )  # "strong", "moderate", "weak", "theoretical"
    population: Mapped[str | None] = mapped_column(
        String(20), default=None
    )  # "pregnancy", "fertility", "lactation", "general"
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    chemical: Mapped["ChemicalIdentity"] = relationship(
        "ChemicalIdentity", back_populates="evidence"
    )
