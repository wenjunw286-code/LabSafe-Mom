"""Analysis trigger and status routes — v3 deterministic pipeline.

Orchestrates the full 10-stage pipeline:
1. Hybrid chemical extraction (dictionary + CAS + regex + LLM fallback)
2. Chemical normalization (name → CAS → canonical identity)
3. Knowledge base lookup (toxicological profiles + evidence)
4. Lab operation detection (ontology-based keyword matching)
5. Exposure analysis (ventilation, temperature, frequency, routes)
6. Rule engine evaluation (deterministic YAML rules — NO LLM)
7. Score calculation (0-100 scores per population)
8. Evidence attachment (every claim cites NIOSH/OSHA/IARC/etc.)
9. Report generation (structured assembly of all data)
10. Quality control (verify completeness + confidence score)
11. LLM summarization (natural language only — NO risk decisions)
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db
from app.db.database import AsyncSessionLocal
from app.models.report import AnalysisReport, IdentifiedSubstance

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Request Schemas ──────────────────────────────────────────────

class AnalyzeTriggerRequest(BaseModel):
    """Request to trigger analysis with optional population selection."""

    population: str = Field(
        default="pregnancy",
        description="Target population: pregnancy, fertility, or lactation",
        pattern="^(pregnancy|fertility|lactation)$",
    )


class AnalyzeTriggerResponse(BaseModel):
    id: int
    status: str


class AnalyzeStatusResponse(BaseModel):
    id: int
    status: str
    progress: str


# ── Pipeline ─────────────────────────────────────────────────────

async def _run_analysis_v3(report_id: int, population: str = "pregnancy") -> None:
    """Execute the full v3 deterministic analysis pipeline.

    This replaces the old LLM-heavy pipeline with a deterministic,
    evidence-based multi-stage architecture.

    DB sessions are kept short to avoid SQLite lock contention:
    - Phase 1: Open DB → load report + KB lookup → close DB
    - Phase 2: Pure computation (no DB) — rule engine, scoring, report gen
    - Phase 3: LLM summarization (no DB, can be slow)
    - Phase 4: Open DB → persist results → close DB
    """
    import asyncio
    import time

    t_start = time.monotonic()

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: DB-dependent operations (keep session brief)
    # ═══════════════════════════════════════════════════════════════
    async with AsyncSessionLocal() as db:
        try:
            # ── Load report ───────────────────────────────────────
            result = await db.execute(
                select(AnalysisReport).where(AnalysisReport.id == report_id)
            )
            report = result.scalar_one_or_none()
            if not report:
                logger.error("analysis_report_not_found", report_id=report_id)
                return

            report.status = "processing"
            await db.commit()

            text = report.extracted_text or ""
            if not text or len(text.strip()) < 10:
                logger.warning("analysis_empty_text", report_id=report_id)
                report.status = "failed"
                report.error_message = "No text extracted from protocol file"
                await db.commit()
                return

            # ── STAGE 1: Hybrid Chemical Extraction ───────────────
            logger.info("stage1_extraction_start", report_id=report_id)
            from app.services.extraction.pipeline import HybridExtractionPipeline

            extractor = HybridExtractionPipeline(db)
            extraction_result = await extractor.extract(text)
            normalized_chemicals = extraction_result.chemicals

            logger.info(
                "stage1_extraction_done",
                total=extraction_result.total_raw_extractions,
                resolved=extraction_result.resolved_count,
                methods=extraction_result.extraction_methods_used,
                llm_fallback=extraction_result.llm_fallback_used,
            )

            if not normalized_chemicals:
                logger.info("analysis_no_chemicals", report_id=report_id)
                report.report_json = _build_empty_report(
                    report.original_filename, population, extraction_result
                )
                report.overall_risk = "Low"
                report.overall_score = 0
                report.status = "completed"
                await db.commit()
                return

            # ── STAGE 2: Knowledge Base Lookup ────────────────────
            logger.info("stage2_kb_lookup_start", report_id=report_id)
            from app.services.knowledge.kb_lookup import KnowledgeBaseLookup

            kb = KnowledgeBaseLookup(db)
            identity_ids = [
                n.chemical_identity_id
                for n in normalized_chemicals
                if n.chemical_identity_id is not None
            ]
            chemical_profiles = await kb.lookup_batch(identity_ids) if identity_ids else []

            # Map profiles to dict for rule engine
            chemical_dicts = []
            for n in normalized_chemicals:
                profile = next(
                    (p for p in chemical_profiles if p.get("id") == n.chemical_identity_id),
                    None,
                )
                if not profile:
                    profile = await kb.lookup_by_identifier(
                        cas=n.cas_number,
                        names=[n.canonical_name_en, n.canonical_name_zh, n.raw_name],
                    )
                if profile:
                    chemical_dicts.append(profile)
                else:
                    chemical_dicts.append({
                        "id": None,
                        "canonical_name_en": n.raw_name,
                        "cas_number": n.cas_number,
                        "reproductive_toxin": False,
                        "teratogen": False,
                        "mutagen": False,
                        "carcinogen_class": None,
                        "pregnancy_category": None,
                        "lactation_risk_category": None,
                        "placental_transfer": None,
                        "volatile": None,
                        "dermal_absorption": None,
                        "acute_toxicity_ld50": None,
                        "engineering_controls": None,
                        "osha_pel": None,
                        "niosh_rel": None,
                        "data_source": "unresolved",
                        "evidence_level": "D",
                    })

            logger.info(
                "stage2_kb_lookup_done",
                profiles=sum(1 for c in chemical_dicts if c.get("id")),
                total=len(chemical_dicts),
            )

            chemical_dicts = _dedupe_chemical_dicts(chemical_dicts)
            logger.info(
                "stage2_kb_dedup_done",
                total=len(chemical_dicts),
                substances=[c.get("canonical_name_en") for c in chemical_dicts],
            )

            # Save metadata we'll need after DB close
            _original_filename = report.original_filename
            _extraction_methods = extraction_result.extraction_methods_used
            _llm_fallback = extraction_result.llm_fallback_used
            _total_raw = extraction_result.total_raw_extractions
            _resolved = sum(1 for c in chemical_dicts if c.get("id"))

        except Exception as exc:
            logger.error("analysis_phase1_failed", report_id=report_id, error=str(exc), exc_info=True)
            try:
                await db.rollback()
                result = await db.execute(
                    select(AnalysisReport).where(AnalysisReport.id == report_id)
                )
                report = result.scalar_one_or_none()
                if report:
                    report.status = "failed"
                    report.error_message = str(exc)[:1000]
                    await db.commit()
            except Exception:
                pass
            return

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: Pure computation (NO DB — no SQLite locks)
    # ═══════════════════════════════════════════════════════════════
    try:
        # ── STAGE 3: Lab Operation Detection ────────────────────
        logger.info("stage3_ontology_start", report_id=report_id)
        from app.services.ontology.operations import get_operation_detector

        op_detector = get_operation_detector()
        detected_ops = op_detector.detect(text)

        logger.info(
            "stage3_ontology_done",
            operations=len(detected_ops),
            ops=[op.name_en for op in detected_ops],
        )

        # ── STAGE 4: Exposure Analysis ───────────────────────────
        logger.info("stage4_exposure_start", report_id=report_id)
        from app.services.exposure.analyzer import get_exposure_analyzer

        exp_analyzer = get_exposure_analyzer()
        exposure_profiles = exp_analyzer.analyze(text, detected_ops, chemical_dicts)

        logger.info("stage4_exposure_done", profiles=len(exposure_profiles))

        # ── STAGE 5: Rule Engine Evaluation ──────────────────────
        logger.info("stage5_rules_start", report_id=report_id)
        from app.services.rules.engine import get_rule_engine

        rule_engine = get_rule_engine()

        ops_data = [
            {
                "operation_id": op.operation_id,
                "aerosol_generation": op.aerosol_generation,
                "volatile_release": op.volatile_release,
                "powder_handling": op.powder_handling,
                "requires_containment": op.requires_containment,
                "primary_exposure_route": op.primary_exposure_route,
                "secondary_exposure_routes": op.secondary_exposure_routes,
                "risk_modifier": op.risk_modifier,
            }
            for op in detected_ops
        ]

        all_rule_results = rule_engine.evaluate_all(
            chemicals=chemical_dicts,
            exposures=[e.to_dict() for e in exposure_profiles],
            operations=ops_data,
        )

        logger.info("stage5_rules_done", rules_fired=len(all_rule_results))

        # ── STAGE 6: Score Calculation ───────────────────────────
        logger.info("stage6_scoring_start", report_id=report_id)
        from app.services.risk.score_calculator import ScoreCalculator

        calculator = ScoreCalculator()
        overall_score = calculator.calculate(
            rule_results=all_rule_results,
            chemicals=chemical_dicts,
            population=population,
        )

        logger.info(
            "stage6_scoring_done",
            overall_score=overall_score.overall_score,
            overall_risk=overall_score.overall_risk,
            high_risk_count=overall_score.high_risk_count,
        )

        # ── STAGE 7: Evidence Attachment ─────────────────────────
        logger.info("stage7_evidence_start", report_id=report_id)
        from app.services.report.evidence_provider import EvidenceProvider

        evidence_provider = EvidenceProvider()
        evidenced = evidence_provider.provide(overall_score, chemical_dicts)

        logger.info(
            "stage7_evidence_done",
            citations=evidenced.total_citations,
            sources=evidenced.sources_used,
        )

        # ── STAGE 8: Report Generation ───────────────────────────
        logger.info("stage8_report_start", report_id=report_id)
        from app.services.report.generator import ReportGeneratorV3

        report_gen = ReportGeneratorV3()
        report_json = report_gen.generate(
            evidenced=evidenced,
            operations=detected_ops,
            exposures=exposure_profiles,
            population=population,
            original_filename=_original_filename,
            extraction_metadata={
                "methods_used": _extraction_methods,
                "llm_fallback_used": _llm_fallback,
                "total_raw": _total_raw,
                "resolved": _resolved,
            },
        )

        # ── STAGE 9: Quality Control ─────────────────────────────
        logger.info("stage9_qc_start", report_id=report_id)
        from app.services.report.qc_checker import QCChecker

        qc = QCChecker()
        raw_names = [n.raw_name for n in normalized_chemicals]
        qc_result = qc.verify(
            report=report_json,
            raw_extractions=raw_names,
            normalized_chemicals=chemical_dicts,
            rule_results=all_rule_results,
        )

        report_json["metadata"]["qc"] = {
            "passed": qc_result.passed,
            "confidence_score": qc_result.confidence_score,
            "issues": qc_result.issues,
            "warnings": qc_result.warnings,
            "stats": qc_result.stats,
        }

        if qc_result.issues:
            report_json["qc_warnings"] = qc_result.issues

        logger.info(
            "stage9_qc_done",
            passed=qc_result.passed,
            confidence=qc_result.confidence_score,
            issues=len(qc_result.issues),
        )

    except Exception as exc:
        logger.error("analysis_phase2_failed", report_id=report_id, error=str(exc), exc_info=True)
        async with AsyncSessionLocal() as db2:
            result = await db2.execute(
                select(AnalysisReport).where(AnalysisReport.id == report_id)
            )
            report = result.scalar_one_or_none()
            if report:
                report.status = "failed"
                report.error_message = str(exc)[:1000]
                await db2.commit()
        return

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: LLM Summarization (NO DB — can be slow, safe to hang)
    # ═══════════════════════════════════════════════════════════════
    logger.info("stage10_llm_summary_start", report_id=report_id)
    try:
        from app.services.llm.summarizer import LLMSummarizer

        summarizer = LLMSummarizer()
        summary = await asyncio.wait_for(
            summarizer.summarize(report_json, population),
            timeout=45.0,  # Hard timeout — use fallback if LLM is slow
        )
        report_json["executive_summary"]["summary_text"] = summary.summary_text
        report_json["executive_summary"]["key_findings"] = summary.key_findings
        report_json["executive_summary"]["general_recommendation"] = (
            summary.general_recommendation
        )
        logger.info("stage10_llm_summary_done")
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("llm_summary_skipped", error=str(exc))

    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: Persist Results (new short-lived DB session)
    # ═══════════════════════════════════════════════════════════════
    logger.info("stage11_persist_start", report_id=report_id)
    async with AsyncSessionLocal() as db3:
        try:
            result = await db3.execute(
                select(AnalysisReport).where(AnalysisReport.id == report_id)
            )
            report = result.scalar_one_or_none()
            if not report:
                logger.error("analysis_report_lost", report_id=report_id)
                return

            # Persist identified substances (backward compatible)
            for item in report_json.get("identified_hazardous_materials", []):
                identified = IdentifiedSubstance(
                    report_id=report.id,
                    substance_name=item.get("substance_name", "Unknown"),
                    category=item.get("category", ""),
                    pregnancy_risk=item.get("pregnancy_risk", "Unknown"),
                    fertility_risk=item.get("fertility_risk", "Unknown"),
                    lactation_risk=item.get("lactation_risk", "Unknown"),
                    risk_reason=item.get("risk_reason", ""),
                    effects_on_fetus=item.get("effects_on_fetus") or "",
                    effects_on_reproduction=item.get("effects_on_reproduction") or "",
                    effects_on_breastfeeding=item.get("effects_on_breastfeeding") or "",
                    exposure_routes=[],
                    recommended_ppe=item.get("recommended_ppe") or "",
                    recommended_precautions=item.get("recommended_precautions") or "",
                    found_in_section="",
                    from_database=item.get("data_source") != "unresolved",
                )
                db3.add(identified)

            # Persist rule evaluations for audit trail
            try:
                from app.models.lab_operation import RuleEvaluation as RuleEvalModel

                for rr in all_rule_results:
                    db3.add(
                        RuleEvalModel(
                            report_id=report.id,
                            chemical_identity_id=None,
                            substance_name=rr.substance_name,
                            rule_id=rr.rule_id,
                            rule_name=rr.rule_name,
                            score_contribution=rr.score_contribution,
                            rule_reason=rr.rule_reason,
                            population=rr.population,
                        )
                    )
            except Exception as exc:
                logger.warning("rule_evaluation_persist_failed", error=str(exc))

            # Persist detected operations
            try:
                from app.models.lab_operation import DetectedOperation as DetectedOpModel
                from app.models.lab_operation import LabOperation
                from sqlalchemy import select as sel

                for op in detected_ops:
                    op_result = await db3.execute(
                        sel(LabOperation).where(LabOperation.name_en == op.name_en)
                    )
                    op_db = op_result.scalar_one_or_none()
                    if op_db:
                        db3.add(
                            DetectedOpModel(
                                report_id=report.id,
                                operation_id=op_db.id,
                                found_in_section=op.found_in_section,
                            )
                        )
            except Exception as exc:
                logger.warning("detected_operations_persist_failed", error=str(exc))

            # Finalize report
            report.report_json = report_json
            report.overall_risk = report_json["overall_risk"]
            report.overall_score = report_json["overall_score"]
            report.status = "completed"
            await db3.commit()

            elapsed = time.monotonic() - t_start
            logger.info(
                "analysis_v3_completed",
                report_id=report_id,
                substances=len(normalized_chemicals),
                score=report_json["overall_score"],
                risk=report_json["overall_risk"],
                rules_fired=len(all_rule_results),
                evidence_citations=evidenced.total_citations,
                qc_confidence=qc_result.confidence_score,
                elapsed_s=round(elapsed, 2),
            )

        except Exception as exc:
            logger.error(
                "analysis_v3_persist_failed",
                report_id=report_id,
                error=str(exc),
                exc_info=True,
            )
            await db3.rollback()
            try:
                result = await db3.execute(
                    select(AnalysisReport).where(AnalysisReport.id == report_id)
                )
                report = result.scalar_one_or_none()
                if report:
                    report.status = "failed"
                    report.error_message = str(exc)[:1000]
                    await db3.commit()
            except Exception as inner_exc:
                logger.error("analysis_failed_status_update", error=str(inner_exc))


def _build_empty_report(
    filename: str,
    population: str,
    extraction_result,
) -> dict:
    """Build an empty report when no chemicals are found."""
    from datetime import datetime, timezone

    return {
        "original_filename": filename,
        "overall_risk": "Low",
        "overall_score": 0,
        "executive_summary": {
            "overall_risk": "Low",
            "overall_score": 0,
            "total_substances": 0,
            "high_risk_count": 0,
            "critical_count": 0,
            "population": population,
            "summary_text": "No hazardous chemical substances were identified in this protocol.",
        },
        "identified_hazardous_materials": [],
        "population_risk": {
            "pregnancy": {"max_score": 0, "risk_level": "Low", "substances_at_risk": []},
            "fertility": {"max_score": 0, "risk_level": "Low", "substances_at_risk": []},
            "lactation": {"max_score": 0, "risk_level": "Low", "substances_at_risk": []},
        },
        "exposure_analysis": {"operations_detected": [], "profiles": []},
        "safety_controls": {
            "engineering_controls": [],
            "recommended_ppe": [],
            "operational_procedures": [],
        },
        "evidence_summary": {"total_citations": 0, "sources_used": [], "general_evidence": []},
        "metadata": {
            "version": "3.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline": {"extraction": {"methods_used": []}},
            "qc": {"passed": True, "confidence_score": 1.0},
        },
        "disclaimer": "No hazardous substances identified. This does not guarantee safety.",
    }


# ── Routes ───────────────────────────────────────────────────────

def _dedupe_chemical_dicts(chemicals: list[dict]) -> list[dict]:
    """Deduplicate CAS/name repeats while keeping the more conservative profile."""
    by_key: dict[str, dict] = {}
    order: list[str] = []
    for chem in chemicals:
        key = _chemical_dedupe_key(chem)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = chem
            order.append(key)
            continue
        by_key[key] = _pick_more_conservative(existing, chem)
    return [by_key[key] for key in order]


def _chemical_dedupe_key(chem: dict) -> str:
    cas = chem.get("cas_number")
    if cas:
        return f"cas:{cas}"
    name = (chem.get("canonical_name_en") or chem.get("substance_name") or "unknown").lower()
    return f"name:{name}"


def _pick_more_conservative(left: dict, right: dict) -> dict:
    return right if _risk_rank(right) > _risk_rank(left) else left


def _risk_rank(chem: dict) -> int:
    values = [
        chem.get("pregnancy_risk"),
        chem.get("fertility_risk"),
        chem.get("lactation_risk"),
    ]
    return max((_risk_value(v) for v in values), default=0)


def _risk_value(value: str | None) -> int:
    text = str(value or "").lower()
    if "critical" in text:
        return 4
    if "high" in text:
        return 3
    if "moderate" in text:
        return 2
    if "low" in text:
        return 1
    return 0


@router.post("/analyze/{report_id}", response_model=AnalyzeTriggerResponse)
async def trigger_analysis(
    report_id: int,
    background_tasks: BackgroundTasks,
    request: AnalyzeTriggerRequest | None = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Trigger v3 deterministic safety analysis for an uploaded protocol.

    The analysis runs in the background through all 10 pipeline stages.
    Poll GET /analyze/{id}/status for progress.

    Args:
        report_id: Uploaded report ID
        request: Optional population selection (default: pregnancy)
    """
    population = request.population if request else "pregnancy"

    result = await db.execute(
        select(AnalysisReport).where(AnalysisReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status == "processing":
        raise HTTPException(status_code=400, detail="Analysis already in progress")

    if report.status == "completed":
        return AnalyzeTriggerResponse(id=report.id, status="completed")

    report.status = "processing"
    await db.commit()

    background_tasks.add_task(_run_analysis_v3, report_id, population)

    logger.info(
        "analysis_v3_triggered",
        report_id=report_id,
        population=population,
    )
    return AnalyzeTriggerResponse(id=report.id, status="processing")


@router.get("/analyze/{report_id}/status", response_model=AnalyzeStatusResponse)
async def get_analysis_status(
    report_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Poll for the current analysis status."""
    result = await db.execute(
        select(AnalysisReport).where(AnalysisReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    progress_map = {
        "pending": "Waiting to start analysis...",
        "processing": "Analyzing protocol — extracting chemicals, evaluating risks, generating report...",
        "completed": "Analysis complete",
        "failed": f"Analysis failed: {report.error_message or 'Unknown error'}",
    }
    progress = progress_map.get(report.status, report.status)

    return AnalyzeStatusResponse(
        id=report.id,
        status=report.status,
        progress=progress,
    )
