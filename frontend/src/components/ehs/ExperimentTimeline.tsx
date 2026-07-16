"use client";

import { useState } from "react";
import { Clock, AlertTriangle, ChevronRight, Beaker, Shield } from "lucide-react";
import type { SubstanceItem } from "@/lib/types";
import { cn } from "@/lib/utils";

// ── Build timeline from substances' found_in_section ──────────
interface TimelineStep {
  label: string;
  substances: SubstanceItem[];
  isHighRisk: boolean;
  exposureNotes: string[];
}

function buildTimeline(substances: SubstanceItem[]): TimelineStep[] {
  if (substances.length === 0) return [];

  // Group substances by section context
  const steps: TimelineStep[] = [];
  const seen = new Set<string>();

  for (const s of substances) {
    const section = s.found_in_section || "General Protocol";
    // Extract a short label: first 40 chars or first sentence
    const label = section.length > 50 ? section.slice(0, 50) + "..." : section;

    if (!seen.has(label)) {
      seen.add(label);
      steps.push({
        label,
        substances: [],
        isHighRisk: false,
        exposureNotes: [],
      });
    }

    const step = steps.find((st) => st.label === label)!;
    step.substances.push(s);

    if ([s.pregnancy_risk, s.fertility_risk, s.lactation_risk].some((r) => r === "High Risk")) {
      step.isHighRisk = true;
    }

    // Derive exposure notes from exposure routes
    const routes = s.exposure_routes || [];
    if (routes.includes("吸入")) step.exposureNotes.push("Inhalation risk");
    if (routes.includes("气溶胶")) step.exposureNotes.push("Aerosol generation");
    if (routes.includes("皮肤接触")) step.exposureNotes.push("Dermal contact");
  }

  // De-duplicate exposure notes
  for (const step of steps) {
    step.exposureNotes = Array.from(new Set(step.exposureNotes));
  }

  return steps;
}

// ── Component ────────────────────────────────────────────────
export default function ExperimentTimeline({ substances }: { substances: SubstanceItem[] }) {
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const steps = buildTimeline(substances);

  if (steps.length === 0) return null;

  return (
    <section className="med-card p-6 mb-6 animate-slide-up">
      <h2 className="section-title">
        <span className="section-icon bg-rose-50 text-rose-600">
          <Clock className="w-4 h-4" />
        </span>
        Experimental Timeline
      </h2>
      <p className="text-xs text-neutral-400 mb-5">
        Reconstructed from protocol sections. High-risk steps are highlighted.
      </p>

      {/* ── Screen: absolute-positioned timeline ── */}
      <div className="relative pl-8 print:pl-0">
        {/* Vertical line — hidden in print */}
        <div className="absolute left-[15px] top-2 bottom-2 w-0.5 bg-neutral-200 print:hidden" />
        {/* Print-only left border as timeline connector */}
        <div className="hidden print:block print:border-l-2 print:border-neutral-300 print:pl-6 print:-ml-1">
          <div className="space-y-3">
            {steps.map((step, i) => (
              <div key={i} className="print:pb-3">
                {/* Print step header with inline dot */}
                <div className="hidden print:flex print:items-center print:gap-2 print:mb-1">
                  <span className={cn(
                    "w-3 h-3 rounded-full border-2 flex-shrink-0",
                    step.isHighRisk ? "border-red-500 bg-red-100" : "border-neutral-400 bg-white"
                  )} />
                  <span className="text-xs font-bold text-neutral-700 uppercase tracking-wider">
                    Step {i + 1}
                  </span>
                  {step.isHighRisk && (
                    <span className="text-xs font-bold text-red-700">⚠ HIGH RISK</span>
                  )}
                </div>
                <p className="hidden print:block print:text-sm print:font-semibold print:text-neutral-900 print:mb-1">
                  {step.label}
                </p>
                <p className="hidden print:block print:text-xs print:text-neutral-500 print:mb-2">
                  {step.substances.length} substance{step.substances.length !== 1 ? "s" : ""}: {step.substances.map((s) => s.substance_name).join(", ")}
                </p>
                {/* Print exposure notes */}
                {step.exposureNotes.length > 0 && (
                  <div className="hidden print:block print:mb-2">
                    <span className="text-xs font-semibold text-neutral-600">Exposure: </span>
                    <span className="text-xs text-neutral-600">{step.exposureNotes.join(" · ")}</span>
                  </div>
                )}
                {/* Print controls */}
                <div className="hidden print:block print:text-xs print:text-neutral-600">
                  <span className="font-semibold">Controls: </span>
                  {step.isHighRisk && "Fume hood · "}Double gloves{step.exposureNotes.includes("Inhalation risk") && " · Respirator"}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Screen: interactive timeline ── */}
        <div className="space-y-1 print:hidden">
          {steps.map((step, i) => (
            <div key={i} className="relative pb-4 last:pb-0">
              {/* Dot */}
              <div
                className={cn(
                  "absolute -left-[23px] top-1.5 w-4 h-4 rounded-full border-2 bg-white transition-colors",
                  step.isHighRisk ? "border-red-400 bg-red-50" : "border-rose-300",
                )}
              />

              <button
                onClick={() => setActiveStep(activeStep === i ? null : i)}
                className={cn(
                  "w-full text-left p-4 rounded-xl transition-all duration-200",
                  step.isHighRisk
                    ? "bg-red-50/50 border border-red-100 hover:bg-red-50"
                    : "bg-neutral-50/80 border border-neutral-100 hover:bg-neutral-100/50",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">
                        Step {i + 1}
                      </span>
                      {step.isHighRisk && (
                        <span className="med-badge med-badge-high flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          High Risk
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-semibold text-neutral-800 leading-relaxed">
                      {step.label}
                    </p>
                    <p className="text-2xs text-neutral-400 mt-1">
                      {step.substances.length} substance{step.substances.length !== 1 ? "s" : ""}: {step.substances.map((s) => s.substance_name).join(", ")}
                    </p>
                  </div>
                  <ChevronRight
                    className={cn(
                      "w-4 h-4 text-neutral-400 mt-1 transition-transform flex-shrink-0",
                      activeStep === i && "rotate-90",
                    )}
                  />
                </div>

                {/* Expanded details */}
                {activeStep === i && (
                  <div className="mt-3 pt-3 border-t border-neutral-200 animate-expand-down">
                    {step.exposureNotes.length > 0 && (
                      <div className="mb-3">
                        <p className="text-2xs font-semibold text-neutral-500 uppercase tracking-wider mb-1.5">
                          Exposure Notes
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {step.exposureNotes.map((n) => (
                            <span key={n} className="tag bg-orange-50 text-orange-700 border border-orange-200">
                              {n}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div>
                      <p className="text-2xs font-semibold text-neutral-500 uppercase tracking-wider mb-1.5">
                        Controls Recommended
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {step.isHighRisk && (
                          <span className="tag bg-rose-50 text-rose-700 border border-rose-200">
                            <Shield className="w-3 h-3" /> Fume hood
                          </span>
                        )}
                        <span className="tag bg-rose-50 text-rose-700 border border-rose-200">
                          <Shield className="w-3 h-3" /> Double gloves
                        </span>
                        {step.exposureNotes.includes("Inhalation risk") && (
                          <span className="tag bg-rose-50 text-rose-700 border border-rose-200">
                            <Shield className="w-3 h-3" /> Respirator
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
