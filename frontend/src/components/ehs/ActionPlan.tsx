"use client";

import { AlertTriangle, ArrowRight, ShieldCheck, Wind } from "lucide-react";
import type { ReportDetail, SubstanceItem } from "@/lib/types";

function isHighRisk(substance: SubstanceItem) {
  return [substance.pregnancy_risk, substance.fertility_risk, substance.lactation_risk].some((risk) =>
    String(risk || "").includes("High"),
  );
}

function topRule(substance: SubstanceItem) {
  return substance.fired_rules?.find((rule) => rule.score_contribution > 0)?.reason || substance.risk_reason || "Review this substance with EHS before use.";
}

function controlFor(substance: SubstanceItem) {
  const text = `${substance.recommended_precautions || ""} ${substance.risk_reason || ""}`.toLowerCase();
  if (text.includes("fume") || text.includes("hood") || text.includes("vent")) {
    return "Move this step into a certified fume hood and keep containers capped.";
  }
  if (text.includes("powder") || text.includes("dust")) {
    return "Use enclosed weighing, avoid dust, and assign powder handling to trained staff.";
  }
  if (text.includes("lead")) {
    return "Use lead-specific waste segregation and surface decontamination.";
  }
  return "Minimize handling time, use double gloves, and document EHS approval.";
}

export default function ActionPlan({ report }: { report: ReportDetail }) {
  const substances = report.identified_hazardous_materials || [];
  const highRisk = substances.filter(isHighRisk);
  const controls = report._v3?.safety_controls || report.safety_controls;

  return (
    <section className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="med-card p-4">
          <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">Decision</p>
          <p className="mt-1 text-lg font-bold text-neutral-900">
            {highRisk.length > 0 ? "EHS review required" : "Routine controls"}
          </p>
        </div>
        <div className="med-card p-4">
          <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">High-risk items</p>
          <p className="mt-1 text-lg font-bold text-neutral-900">{highRisk.length}</p>
        </div>
        <div className="med-card p-4">
          <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">Evidence sources</p>
          <p className="mt-1 text-lg font-bold text-neutral-900">
            {report._v3?.evidence_summary?.sources_used?.length || report.evidence_summary?.sources_used?.length || 0}
          </p>
        </div>
      </div>

      {highRisk.length > 0 && (
        <div className="space-y-3">
          {highRisk.slice(0, 6).map((substance) => (
            <div key={`${substance.substance_name}-${substance.cas_number || ""}`} className="med-card border-l-[3px] border-l-red-500 p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-700">
                  <AlertTriangle className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-neutral-900">{substance.substance_name}</h3>
                    {substance.cas_number && <span className="tag bg-neutral-50 text-neutral-600 border border-neutral-200">CAS {substance.cas_number}</span>}
                  </div>
                  <p className="mt-2 text-sm text-neutral-600">{topRule(substance)}</p>
                  <div className="mt-3 flex items-start gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-900">
                    <ArrowRight className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    <span>{controlFor(substance)}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="med-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="h-4 w-4 text-sage-700" />
          <h3 className="font-bold text-neutral-900">Protocol-level controls</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-neutral-700">
          {(controls?.engineering_controls || []).slice(0, 4).map((item) => (
            <div key={item} className="flex gap-2 rounded-lg bg-neutral-50 p-3">
              <Wind className="mt-0.5 h-4 w-4 flex-shrink-0 text-neutral-400" />
              <span>{item}</span>
            </div>
          ))}
          {(controls?.operational_procedures || []).slice(0, 4).map((item) => (
            <div key={item} className="flex gap-2 rounded-lg bg-neutral-50 p-3">
              <ShieldCheck className="mt-0.5 h-4 w-4 flex-shrink-0 text-neutral-400" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

