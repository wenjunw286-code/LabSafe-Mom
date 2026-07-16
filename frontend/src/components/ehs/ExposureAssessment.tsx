"use client";

import { Wind, AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";
import type { SubstanceItem } from "@/lib/types";
import { cn } from "@/lib/utils";

// ── Derive exposure profile from substances ───────────────────
interface ExposureFinding {
  label: string;
  detected: boolean;
  severity: "high" | "moderate" | "low";
  detail: string;
}

function analyzeExposures(substances: SubstanceItem[]): {
  findings: ExposureFinding[];
  overallRisk: "High" | "Moderate" | "Low";
  summary: string;
} {
  const allRoutes = substances.flatMap((s) => s.exposure_routes || []);
  const allPrecautions = substances.map((s) => s.recommended_precautions || "").join(" ");

  const findings: ExposureFinding[] = [
    {
      label: "Open container handling",
      detected: allPrecautions.includes("通风橱") || allRoutes.includes("吸入"),
      severity: "high",
      detail: "Chemical fume hood recommended — indicates open handling of volatiles",
    },
    {
      label: "Volatile chemicals",
      detected: allRoutes.includes("吸入") || allRoutes.includes("气溶胶"),
      severity: "high",
      detail: "Inhalation risk from volatile organic solvents or fixatives",
    },
    {
      label: "Aerosol generation",
      detected: allRoutes.includes("气溶胶"),
      severity: "high",
      detail: "Procedures may generate aerosols (centrifugation, vortexing, sonication)",
    },
    {
      label: "Powder handling",
      detected: allPrecautions.includes("粉末") || allPrecautions.includes("称量"),
      severity: "moderate",
      detail: "Powder weighing may cause inhalation or dermal exposure",
    },
    {
      label: "Pipetting / liquid transfer",
      detected: substances.length > 0, // always true if substances found
      severity: "moderate",
      detail: "Routine liquid handling — risk depends on substance volatility",
    },
    {
      label: "Heating operations",
      detected: allPrecautions.includes("加热") || allPrecautions.includes("温度"),
      severity: "moderate",
      detail: "Heating may increase volatilization of solvents",
    },
    {
      label: "Centrifugation",
      detected: allRoutes.includes("气溶胶") || allPrecautions.includes("离心"),
      severity: "low",
      detail: "Aerosol generation risk during high-speed centrifugation",
    },
  ];

  const highCount = findings.filter((f) => f.detected && f.severity === "high").length;
  const overallRisk = highCount >= 2 ? "High" : highCount >= 1 ? "Moderate" : "Low";

  const summary = overallRisk === "High"
    ? "Multiple high-severity exposure pathways detected. Enhanced engineering controls are essential."
    : overallRisk === "Moderate"
      ? "Some exposure risks identified. Standard PPE with selected engineering controls should suffice."
      : "Limited exposure pathways detected under standard laboratory conditions.";

  return { findings, overallRisk, summary };
}

// ── Component ────────────────────────────────────────────────
export default function ExposureAssessment({ substances }: { substances: SubstanceItem[] }) {
  const { findings, overallRisk, summary } = analyzeExposures(substances);

  const riskStyle = {
    High: "bg-red-50 border-red-200 text-red-800",
    Moderate: "bg-amber-50 border-amber-200 text-amber-800",
    Low: "bg-rose-50 border-rose-200 text-rose-800",
  }[overallRisk];

  return (
    <section className="med-card p-6 mb-6 animate-slide-up">
      <h2 className="section-title">
        <span className="section-icon bg-orange-50 text-orange-700">
          <Wind className="w-4 h-4" />
        </span>
        Exposure Assessment
      </h2>

      {/* ── Overall Risk Banner ────────────────── */}
      <div className={cn("border rounded-xl p-4 mb-5", riskStyle)}>
        <div className="flex items-center gap-2 mb-1">
          <AlertTriangle className="w-4 h-4" />
          <span className="font-bold text-sm">Exposure Risk: {overallRisk}</span>
        </div>
        <p className="text-sm leading-relaxed">{summary}</p>
      </div>

      {/* ── Exposure Checklist ─────────────────── */}
      <div className="space-y-1">
        {findings.map((f) => (
          <div
            key={f.label}
            className={cn(
              "flex items-start gap-3 py-3 px-4 rounded-xl transition-colors",
              f.detected ? "bg-neutral-50" : "opacity-50",
            )}
          >
            <div className="mt-0.5 flex-shrink-0">
              {f.detected ? (
                <CheckCircle2 className={cn(
                  "w-4 h-4",
                  f.severity === "high" ? "text-red-500" :
                  f.severity === "moderate" ? "text-amber-500" : "text-rose-500"
                )} />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-neutral-300" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={cn("text-sm font-medium", f.detected ? "text-neutral-800" : "text-neutral-400")}>
                  {f.label}
                </span>
                {f.detected && (
                  <span className={cn(
                    "tag",
                    f.severity === "high" ? "bg-red-50 text-red-700 border-red-200" :
                    f.severity === "moderate" ? "bg-amber-50 text-amber-700 border-amber-200" :
                    "bg-rose-50 text-rose-700 border-rose-200"
                  )}>
                    {f.severity.toUpperCase()}
                  </span>
                )}
              </div>
              {f.detected && (
                <p className="text-2xs text-neutral-400 mt-0.5">{f.detail}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-start gap-2 text-xs text-neutral-400 mt-4 pt-4 border-t border-neutral-200">
        <HelpCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
        <span>Exposure assessment is derived from detected exposure routes and recommended controls in the protocol text. Actual exposure levels depend on specific laboratory conditions.</span>
      </div>
    </section>
  );
}
