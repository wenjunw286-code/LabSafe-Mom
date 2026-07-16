"""Report retrieval and substance search routes — async."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db
from app.models.report import AnalysisReport, IdentifiedSubstance
from app.models.substance import HazardousSubstance
from app.schemas.report import (
    ExecutiveSummary,
    HighRiskItem,
    PrecautionItem,
    ReportDetail,
    RiskByCategory,
    SubstanceItem,
    SubstanceSearchResponse,
    SubstanceSearchResult,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


def _map_risk_v3_to_v2(risk: str | None) -> str:
    """Map v3 risk labels (Critical/High/Moderate/Low) to v2 format (High Risk/Moderate Risk/Low Risk/Safe)."""
    if not risk:
        return "Unknown"
    mapping = {
        "Critical": "High Risk",
        "High": "High Risk",
        "Moderate": "Moderate Risk",
        "Low": "Low Risk",
    }
    return mapping.get(risk, risk)


def _convert_v3_to_v2(report_json: dict, report_id: int, created_at) -> dict:
    """Convert v3 report_json to v2-compatible format for the frontend.

    The v3 pipeline produces a different JSON structure than what the v2
    frontend expects. This conversion ensures backward compatibility.
    """
    substances_v3 = report_json.get("identified_hazardous_materials", [])
    population_risk = report_json.get("population_risk", {})
    safety_controls = report_json.get("safety_controls", {})
    exposure_analysis = report_json.get("exposure_analysis", {})
    metadata = report_json.get("metadata", {})

    # ── Build legacy risk_by_category ──────────────────────────
    risk_by_category: dict[str, dict] = {}
    for pop_key, pop_label in [("pregnancy", "妊娠期"), ("fertility", "备孕期"), ("lactation", "哺乳期")]:
        pop_data = population_risk.get(pop_key, {})
        risk_by_category[pop_label] = {
            "high": len(pop_data.get("substances_at_risk", [])),
            "moderate": 0,
            "low": max(0, len(substances_v3) - len(pop_data.get("substances_at_risk", []))),
            "safe": 0,
        }

    # ── Build legacy executive_summary ─────────────────────────
    exec_v3 = report_json.get("executive_summary", {})
    high_risk_count = exec_v3.get("high_risk_count", 0)
    total = exec_v3.get("total_substances", len(substances_v3))
    legacy_exec = {
        "total_substances_found": total,
        "high_risk_count": high_risk_count,
        "moderate_risk_count": 0,
        "low_risk_count": max(0, total - high_risk_count),
        "safe_count": 0,
        "summary_text": exec_v3.get("summary_text", ""),
    }

    # ── Build legacy substances ────────────────────────────────
    exposure_profiles = exposure_analysis.get("profiles", [])
    legacy_substances = []
    legacy_high_risk = []
    legacy_precautions = []

    for i, sub in enumerate(substances_v3):
        # Find matching exposure profile
        exp_routes: list[str] = []
        if i < len(exposure_profiles):
            exp_routes = exposure_profiles[i].get("exposure_routes", [])

        preg_risk = _map_risk_v3_to_v2(sub.get("pregnancy_risk"))
        fert_risk = _map_risk_v3_to_v2(sub.get("fertility_risk"))
        lact_risk = _map_risk_v3_to_v2(sub.get("lactation_risk"))

        # Gather PPE from safety_controls
        ppe_list = safety_controls.get("recommended_ppe", [])
        ppe_str = "; ".join(ppe_list) if ppe_list else "Standard lab PPE"

        # Gather precautions from fired rules
        fired_rules = sub.get("fired_rules", [])
        precautions = []
        for fr in fired_rules[:5]:
            if fr.get("reason"):
                precautions.append(fr["reason"])

        legacy_sub = {
            "id": sub.get("id", i + 1),
            "substance_name": sub.get("substance_name", "Unknown"),
            "cas_number": sub.get("cas_number"),
            "category": sub.get("category"),
            "pregnancy_risk": preg_risk,
            "fertility_risk": fert_risk,
            "lactation_risk": lact_risk,
            "pregnancy_score": sub.get("pregnancy_score"),
            "fertility_score": sub.get("fertility_score"),
            "lactation_score": sub.get("lactation_score"),
            "risk_reason": sub.get("risk_reason"),
            "effects_on_fetus": sub.get("effects_on_fetus"),
            "effects_on_reproduction": sub.get("effects_on_reproduction"),
            "effects_on_breastfeeding": sub.get("effects_on_breastfeeding"),
            "exposure_routes": exp_routes,
            "recommended_ppe": sub.get("recommended_ppe") or ppe_str,
            "recommended_precautions": sub.get("recommended_precautions") or ("; ".join(precautions) if precautions else "Use standard laboratory PPE"),
            "found_in_section": None,
            "evidence": sub.get("evidence", []),
            "fired_rules": sub.get("fired_rules", []),
            "ghs_classification": sub.get("ghs_classification"),
            "hazard_statements": sub.get("hazard_statements"),
            "references": sub.get("references"),
            "data_source": sub.get("data_source"),
            "evidence_level": sub.get("evidence_level"),
        }
        legacy_substances.append(legacy_sub)

        # High risk items
        is_high = any(r in ("High Risk",) for r in [preg_risk, fert_risk, lact_risk])
        if is_high:
            legacy_high_risk.append({
                "substance_name": sub.get("substance_name", "Unknown"),
                "category": sub.get("category", ""),
                "pregnancy_risk": preg_risk,
                "fertility_risk": fert_risk,
                "lactation_risk": lact_risk,
                "recommended_precautions": "; ".join(precautions) if precautions else None,
            })

        # Precautions
        if precautions or is_high:
            legacy_precautions.append({
                "substance_name": sub.get("substance_name", "Unknown"),
                "risk": preg_risk,
                "precautions": precautions or ["Use standard laboratory PPE"],
            })

    # Serialize created_at safely
    if created_at is None:
        created_str = None
    elif hasattr(created_at, "isoformat"):
        created_str = created_at.isoformat()
    else:
        created_str = str(created_at)

    return {
        "id": report_id,
        "original_filename": report_json.get("original_filename", ""),
        "overall_risk": _map_risk_v3_to_v2(report_json.get("overall_risk")),
        "overall_score": report_json.get("overall_score"),
        "executive_summary": legacy_exec,
        "identified_hazardous_materials": legacy_substances,
        "high_risk_items": legacy_high_risk,
        "recommended_precautions": legacy_precautions,
        "risk_by_category": risk_by_category,
        "disclaimer": report_json.get("disclaimer", ""),
        "created_at": created_str,
        # Also include full v3 data for components that can use it
        "_v3": {
            "population_risk": population_risk,
            "exposure_analysis": exposure_analysis,
            "safety_controls": safety_controls,
            "evidence_summary": report_json.get("evidence_summary"),
            "metadata": metadata,
            "qc_warnings": report_json.get("qc_warnings"),
            "executive_summary": exec_v3,
        },
    }


@router.get("/report/{report_id}")
async def get_report(report_id: int, db: AsyncSession = Depends(get_async_db)):
    """Retrieve a completed analysis report by ID."""
    result = await db.execute(
        select(AnalysisReport).where(AnalysisReport.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    if report.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"分析尚未完成，当前状态: {report.status}",
        )

    # ── Return stored report_json (v3) converted to v2 format ──
    if report.report_json:
        converted = _convert_v3_to_v2(
            report.report_json, report.id, report.created_at
        )
        return JSONResponse(content=converted)

    # ── Reconstruct from identified_substances (legacy fallback) ──
    sub_result = await db.execute(
        select(IdentifiedSubstance).where(IdentifiedSubstance.report_id == report_id)
    )
    substances = sub_result.scalars().all()

    materials = []
    high_risk = []
    precautions = []

    for s in substances:
        item = {
            "id": s.id,
            "substance_name": s.substance_name,
            "category": s.category,
            "pregnancy_risk": s.pregnancy_risk,
            "fertility_risk": s.fertility_risk,
            "lactation_risk": s.lactation_risk,
            "risk_reason": s.risk_reason,
            "effects_on_fetus": s.effects_on_fetus,
            "effects_on_reproduction": s.effects_on_reproduction,
            "effects_on_breastfeeding": s.effects_on_breastfeeding,
            "exposure_routes": s.exposure_routes,
            "recommended_ppe": s.recommended_ppe,
            "recommended_precautions": s.recommended_precautions,
            "found_in_section": s.found_in_section,
        }
        materials.append(item)

        if any("High" in str(r) for r in [s.pregnancy_risk, s.fertility_risk, s.lactation_risk]):
            high_risk.append({
                "substance_name": s.substance_name,
                "category": s.category or "",
                "pregnancy_risk": s.pregnancy_risk or "Unknown",
                "fertility_risk": s.fertility_risk or "Unknown",
                "lactation_risk": s.lactation_risk or "Unknown",
                "recommended_precautions": s.recommended_precautions,
            })

        if any("High" in str(s.pregnancy_risk) or "Moderate" in str(s.pregnancy_risk)):
            prec_text = s.recommended_precautions or ""
            prec_lines = [
                p.strip().lstrip("✓").strip()
                for p in prec_text.split("\n")
                if p.strip()
            ]
            precautions.append({
                "substance_name": s.substance_name,
                "risk": s.pregnancy_risk or "Unknown",
                "precautions": prec_lines or ["使用标准实验室PPE"],
            })

    return ReportDetail(
        id=report.id,
        original_filename=report.original_filename,
        overall_risk=report.overall_risk,
        overall_score=report.overall_score,
        executive_summary=ExecutiveSummary(
            total_substances_found=len(materials),
            high_risk_count=sum(
                1 for s in substances
                for r in ["pregnancy_risk", "fertility_risk", "lactation_risk"]
                if "High" in str(getattr(s, r, ""))
            ),
            moderate_risk_count=sum(
                1 for s in substances
                for r in ["pregnancy_risk", "fertility_risk", "lactation_risk"]
                if "Moderate" in str(getattr(s, r, ""))
            ),
            low_risk_count=sum(
                1 for s in substances
                for r in ["pregnancy_risk", "fertility_risk", "lactation_risk"]
                if "Low Risk" == str(getattr(s, r, ""))
            ),
            safe_count=sum(
                1 for s in substances
                for r in ["pregnancy_risk", "fertility_risk", "lactation_risk"]
                if "Safe" == str(getattr(s, r, ""))
            ),
            summary_text=f"共识别 {len(materials)} 种物质",
        ),
        identified_hazardous_materials=[SubstanceItem(**m) for m in materials],
        high_risk_items=[HighRiskItem(**h) for h in high_risk],
        recommended_precautions=[PrecautionItem(**p) for p in precautions],
        risk_by_category={
            "妊娠期": RiskByCategory(),
            "备孕期": RiskByCategory(),
            "哺乳期": RiskByCategory(),
        },
        created_at=report.created_at,
    )


@router.get("/substances", response_model=SubstanceSearchResponse)
async def search_substances(
    search: str = Query(default="", description="Search keyword for chemical name"),
    category: str = Query(default="", description="Filter by substance category"),
    risk: str = Query(default="", description="Filter by risk level"),
    db: AsyncSession = Depends(get_async_db),
):
    """Search the local hazardous substances database."""
    from sqlalchemy import and_, or_

    query = select(HazardousSubstance)

    conditions = []
    if search:
        conditions.append(HazardousSubstance.chemical_name.ilike(f"%{search}%"))
    if category:
        conditions.append(HazardousSubstance.category == category)
    if risk:
        conditions.append(
            or_(
                HazardousSubstance.pregnancy_risk == risk,
                HazardousSubstance.fertility_risk == risk,
                HazardousSubstance.lactation_risk == risk,
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    query = query.limit(100)
    result = await db.execute(query)
    rows = result.scalars().all()

    return SubstanceSearchResponse(
        total=len(rows),
        items=[
            SubstanceSearchResult(
                id=r.id,
                chemical_name=r.chemical_name,
                cas_number=r.cas_number,
                category=r.category,
                pregnancy_risk=r.pregnancy_risk,
                fertility_risk=r.fertility_risk,
                lactation_risk=r.lactation_risk,
                ghs_classification=r.ghs_classification,
                hazard_statements=r.hazard_statements,
                effects_on_fetus=r.effects_on_fetus,
                effects_on_reproduction=r.effects_on_reproduction,
                effects_on_breastfeeding=r.effects_on_breastfeeding,
                recommended_ppe=r.recommended_ppe,
                recommended_precautions=r.recommended_precautions,
                references=r.references,
            )
            for r in rows
        ],
    )
