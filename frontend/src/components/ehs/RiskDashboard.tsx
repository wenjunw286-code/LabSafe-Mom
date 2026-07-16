"use client";

import { Shield, Info } from "lucide-react";
import type { ReportDetail } from "@/lib/types";

type RiskLevel = "Critical" | "High" | "Moderate" | "Low";

function classifyRisk(score: number | null): { level: RiskLevel; color: string; bg: string; border: string } {
  const s = score ?? 0;
  if (s >= 75) return { level: "Critical", color: "text-red-800", bg: "bg-red-50", border: "border-red-200" };
  if (s >= 50) return { level: "High", color: "text-orange-700", bg: "bg-orange-50", border: "border-orange-200" };
  if (s >= 25) return { level: "Moderate", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" };
  return { level: "Low", color: "text-sage-700", bg: "bg-sage-50", border: "border-sage-200" };
}

function computeFactorScores(report: ReportDetail) {
  const substances = report.identified_hazardous_materials || [];
  const totalRisk = substances.reduce((sum, s) => {
    const vals = [s.pregnancy_risk, s.fertility_risk, s.lactation_risk];
    const maxRisk = vals.filter((v) => v === "High Risk").length * 10
      + vals.filter((v) => v === "Moderate Risk").length * 5
      + vals.filter((v) => v === "Low Risk").length * 2;
    return sum + maxRisk;
  }, 0);
  const n = Math.max(1, substances.length);
  const chemScore = Math.min(100, Math.round((totalRisk / (n * 30)) * 100));

  const hasVolatile = substances.some((s) =>
    (s.exposure_routes || []).some((r) => r.includes("吸入") || r.includes("气溶胶"))
  );
  const hasOpenHandling = substances.some((s) =>
    (s.recommended_precautions || "").includes("通风橱")
  );
  const exposureScore = (hasVolatile ? 40 : 15) + (hasOpenHandling ? 30 : 10) + 15;

  const highCount = report.executive_summary?.high_risk_count || 0;
  const populationScore = Math.min(100, highCount * 25 + 15);
  const controlScore = substances.some((s) => (s.recommended_ppe || "").length > 20) ? 20 : 60;

  return [
    { label: "Chemical Hazard", pct: chemScore, detail: `${substances.length} substances · ${highCount} high risk` },
    { label: "Exposure Condition", pct: Math.min(100, exposureScore), detail: hasVolatile ? "Volatile · Open handling detected" : "Limited exposure pathways" },
    { label: "Operation Risk", pct: Math.min(100, highCount * 15 + 20), detail: `${highCount} high-risk steps identified` },
    { label: "Population Sensitivity", pct: populationScore, detail: "Pregnancy · Trying to Conceive · Breastfeeding" },
    { label: "Control Measures", pct: controlScore, detail: controlScore > 40 ? "Controls may need enhancement" : "Adequate controls in place" },
  ];
}

function riskReasonText(report: ReportDetail): string[] {
  const reasons: string[] = [];
  const substances = report.identified_hazardous_materials || [];
  if (substances.length > 0) reasons.push(`Identified ${substances.length} chemical substances`);
  const high = report.executive_summary?.high_risk_count || 0;
  if (high > 0) reasons.push(`${high} reproductive hazards detected`);
  const critical = substances.filter((s) =>
    [s.pregnancy_risk, s.fertility_risk, s.lactation_risk].some((r) => r === "High Risk")
  ).length;
  if (critical > 0) reasons.push(`${critical} substances with high reproductive toxicity`);
  if (substances.some((s) => (s.exposure_routes || []).length >= 3)) {
    reasons.push("Multiple exposure routes identified");
  }
  if (substances.some((s) => (s.recommended_precautions || "").includes("通风橱"))) {
    reasons.push("Open handling of volatile chemicals detected");
  }
  return reasons;
}

export default function RiskDashboard({ report }: { report: ReportDetail }) {
  const score = report.overall_score;
  const risk = classifyRisk(score);
  const factors = computeFactorScores(report);
  const reasons = riskReasonText(report);

  return (
    <section className="animate-fade-in">
      {/* ── Header Banner ──────────────────────── */}
      <div className={`${risk.bg} ${risk.border} border rounded-2xl p-5 sm:p-6 mb-5`}>
        <div className="flex flex-col sm:flex-row sm:items-center gap-5">
          {/* Score ring */}
          <div className="relative w-20 h-20 flex-shrink-0">
            <svg className="w-20 h-20 -rotate-90" viewBox="0 0 96 96">
              <circle cx="48" cy="48" r="40" fill="none" stroke="currentColor"
                className="text-neutral-200" strokeWidth="8" />
              <circle cx="48" cy="48" r="40" fill="none" stroke="currentColor"
                className={risk.color.replace("text-", "text-")}
                strokeWidth="8" strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 40}`}
                strokeDashoffset={`${2 * Math.PI * 40 * (1 - (score ?? 0) / 100)}`}
                style={{ transition: "stroke-dashoffset 1.5s ease-out" }} />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`text-2xl font-extrabold ${risk.color}`}>{score ?? "-"}</span>
            </div>
          </div>

          <div className="flex-1">
            <span className={`med-badge ${risk.level === "Critical" ? "med-badge-critical" : risk.level === "High" ? "med-badge-high" : risk.level === "Moderate" ? "med-badge-moderate" : "med-badge-low"}`}>
              {risk.level === "Critical" ? "⚠ CRITICAL RISK" : risk.level === "High" ? "⚠ HIGH RISK" : risk.level === "Moderate" ? "MODERATE RISK" : "LOW RISK"}
            </span>
            <h1 className="text-xl sm:text-2xl font-bold text-neutral-900 mt-3 mb-3">
              Laboratory Safety Assessment Report
            </h1>
            <div className="space-y-1">
              {reasons.map((r, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-neutral-700">
                  <span className="text-neutral-400 mt-1 flex-shrink-0">•</span>
                  <span>{r}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Risk Factor Breakdown ──────────────── */}
      <div className="med-card p-6 mb-6">
        <h2 className="section-title">
          <span className="section-icon bg-rose-50 text-rose-600">
            <Shield className="w-4 h-4" />
          </span>
          Risk Score Breakdown
        </h2>
        <div className="space-y-4">
          {factors.map((f) => (
            <div key={f.label}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-semibold text-neutral-800">{f.label}</span>
                <span className="text-sm font-bold text-neutral-700 tabular-nums">{f.pct}%</span>
              </div>
              <div className="progress-bar">
                <div
                  className={`progress-fill ${f.pct >= 70 ? "bg-red-500" : f.pct >= 40 ? "bg-amber-500" : "bg-sage-500"}`}
                  style={{ width: `${f.pct}%` }}
                />
              </div>
              <p className="text-2xs text-neutral-400 mt-1">{f.detail}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-start gap-2 text-xs text-neutral-400 mb-2">
        <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
        <span>Risk score computed from chemical hazards, exposure conditions, operation risks, population sensitivity, and existing control measures.</span>
      </div>
    </section>
  );
}
