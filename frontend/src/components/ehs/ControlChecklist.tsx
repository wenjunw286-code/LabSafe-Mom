"use client";

import { Shield, CheckSquare, Square } from "lucide-react";
import type { SubstanceItem } from "@/lib/types";
import { cn } from "@/lib/utils";

// ── Derive required controls from substance data ──────────────
interface ControlItem {
  category: "engineering" | "ppe" | "operational";
  label: string;
  required: boolean;
  reason: string;
}

function deriveControls(substances: SubstanceItem[]): ControlItem[] {
  const allPrecautions = substances.map((s) => s.recommended_precautions || "").join(" ");
  const allPpe = substances.map((s) => s.recommended_ppe || "").join(" ");
  const hasVolatile = substances.some((s) => (s.exposure_routes || []).some((r) => r.includes("吸入") || r.includes("气溶胶")));
  const hasHighRisk = substances.some((s) =>
    [s.pregnancy_risk, s.fertility_risk, s.lactation_risk].includes("High Risk")
  );

  return [
    {
      category: "engineering",
      label: "Chemical fume hood",
      required: allPrecautions.includes("通风橱") || hasVolatile,
      reason: "Required for volatile chemicals and open container handling",
    },
    {
      category: "engineering",
      label: "Biosafety cabinet (Class II)",
      required: allPrecautions.includes("生物安全柜") || substances.some((s) => s.category === "生物试剂"),
      reason: "Required for biological agents (lentivirus, adenovirus, etc.)",
    },
    {
      category: "engineering",
      label: "Local exhaust ventilation",
      required: hasVolatile && !allPrecautions.includes("通风橱"),
      reason: "Supplementary ventilation when fume hood not specified",
    },
    {
      category: "ppe",
      label: "Lab coat (full coverage)",
      required: substances.length > 0,
      reason: "Standard PPE for all laboratory work",
    },
    {
      category: "ppe",
      label: "Double gloves (nitrile)",
      required: hasHighRisk || allPpe.includes("双层手套"),
      reason: "Enhanced dermal protection for high-risk substances",
    },
    {
      category: "ppe",
      label: "Safety goggles / face shield",
      required: substances.some((s) => (s.exposure_routes || []).includes("皮肤接触")),
      reason: "Eye protection for splash and aerosol risks",
    },
    {
      category: "ppe",
      label: "Respirator (N95 or higher)",
      required: allPpe.includes("呼吸器") || hasVolatile,
      reason: "Respiratory protection when engineering controls insufficient",
    },
    {
      category: "operational",
      label: "Minimize exposure duration",
      required: hasHighRisk,
      reason: "Reduce cumulative exposure for high-risk substances",
    },
    {
      category: "operational",
      label: "Immediate spill cleanup protocol",
      required: hasHighRisk,
      reason: "Prevent secondary exposure from accidental releases",
    },
    {
      category: "operational",
      label: "No eating/drinking in work area",
      required: true,
      reason: "Standard laboratory safety practice",
    },
  ];
}

// ── Component ────────────────────────────────────────────────
export default function ControlChecklist({ substances }: { substances: SubstanceItem[] }) {
  const controls = deriveControls(substances);

  const categories = {
    engineering: { label: "Engineering Controls", color: "text-rose-700", bg: "bg-rose-50" },
    ppe: { label: "Personal Protective Equipment", color: "text-medical-700", bg: "bg-medical-50" },
    operational: { label: "Operational Procedures", color: "text-rose-700", bg: "bg-rose-50" },
  };

  return (
    <section className="med-card p-6 mb-6 animate-slide-up">
      <h2 className="section-title">
        <span className="section-icon bg-rose-50 text-rose-700">
          <Shield className="w-4 h-4" />
        </span>
        PPE & Control Checklist
      </h2>
      <p className="text-xs text-neutral-400 mb-5">
        Automatically generated based on identified hazards. Review and adapt to your specific laboratory setup.
      </p>

      <div className="space-y-5">
        {(Object.entries(categories) as [string, { label: string; color: string; bg: string }][]).map(([cat, info]) => {
          const items = controls.filter((c) => c.category === cat);
          if (items.length === 0) return null;

          return (
            <div key={cat}>
              <h3 className={cn("text-xs font-bold uppercase tracking-wider mb-3 px-1", info.color)}>
                {info.label}
              </h3>
              <div className="space-y-1">
                {items.map((item) => (
                  <div
                    key={item.label}
                    className={cn(
                      "flex items-start gap-3 py-2.5 px-4 rounded-xl transition-colors",
                      item.required ? "bg-neutral-50" : "opacity-40",
                    )}
                  >
                    <div className="mt-0.5 flex-shrink-0">
                      {item.required ? (
                        <CheckSquare className="w-4 h-4 text-rose-600" />
                      ) : (
                        <Square className="w-4 h-4 text-neutral-300" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className={cn("text-sm font-medium", item.required ? "text-neutral-800" : "text-neutral-400")}>
                        {item.label}
                      </span>
                      {item.required && (
                        <p className="text-2xs text-neutral-400 mt-0.5">{item.reason}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
