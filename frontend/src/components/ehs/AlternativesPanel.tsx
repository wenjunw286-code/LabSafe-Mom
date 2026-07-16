"use client";

import { Lightbulb, ArrowRight, Check, AlertTriangle } from "lucide-react";
import type { SubstanceItem } from "@/lib/types";

// ── Static alternatives database ──────────────────────────────
// In production this would come from the backend
const ALTERNATIVES: Record<string, { alternative: string; improvement: string; compatibility: string; limitations: string }[]> = {
  Formaldehyde: [
    { alternative: "Glyoxal fixation", improvement: "Lower volatility, reduced carcinogenicity", compatibility: "Suitable for most histology and IF protocols", limitations: "Slightly different crosslinking pattern; validate for your specific antibody" },
    { alternative: "Commercial pre-fixed tissue", improvement: "Zero direct exposure", compatibility: "Available for many tissue types", limitations: "Higher cost; limited to pre-prepared samples" },
  ],
  Paraformaldehyde: [
    { alternative: "Commercial 4% PFA solution (pre-made)", improvement: "Eliminates powder weighing exposure", compatibility: "Direct replacement", limitations: "Slightly higher cost; still contains formaldehyde" },
  ],
  Methanol: [
    { alternative: "Ethanol (in some applications)", improvement: "Lower developmental toxicity", compatibility: "Protein precipitation, some fixation protocols", limitations: "Different solvent properties; test for your protocol" },
  ],
  Xylene: [
    { alternative: "Histo-Clear or CitriSolv", improvement: "Lower volatility and toxicity", compatibility: "Tissue processing and clearing", limitations: "Slightly longer processing times" },
  ],
  Toluene: [
    { alternative: "Heptane or cyclohexane", improvement: "Reduced reproductive toxicity", compatibility: "Organic synthesis, extraction", limitations: "Different boiling point; may require protocol adjustment" },
  ],
  Chloroform: [
    { alternative: "Ethyl acetate or MTBE", improvement: "Lower carcinogenicity", compatibility: "Extraction and purification", limitations: "Different solubility profile" },
  ],
  "Ethidium Bromide": [
    { alternative: "SYBR Safe DNA Gel Stain", improvement: "Non-mutagenic; Ames test negative", compatibility: "DNA gel electrophoresis — direct replacement", limitations: "Slightly higher cost; comparable sensitivity" },
  ],
  DAPI: [
    { alternative: "Pre-mixed DAPI mounting medium", improvement: "Eliminates powder handling", compatibility: "Direct replacement for nuclear staining", limitations: "Slightly higher cost" },
  ],
  Isoflurane: [
    { alternative: "Injectable anesthesia (ketamine/xylazine)", improvement: "Eliminates inhalational exposure", compatibility: "Rodent anesthesia protocols", limitations: "Requires veterinary training; different recovery profile" },
  ],
  Acrylamide: [
    { alternative: "Pre-cast gels", improvement: "Zero contact with unpolymerized acrylamide", compatibility: "SDS-PAGE — direct replacement", limitations: "Higher cost; limited gel percentage options" },
  ],
};

function getAlternatives(name: string) {
  // Try exact match, then partial match
  if (ALTERNATIVES[name]) return ALTERNATIVES[name];
  for (const [key, val] of Object.entries(ALTERNATIVES)) {
    if (name.includes(key) || key.includes(name)) return val;
  }
  return null;
}

// ── Component ────────────────────────────────────────────────
export default function AlternativesPanel({ substances }: { substances: SubstanceItem[] }) {
  // Only show alternatives for high-risk substances
  const highRiskSubstances = substances.filter((s) =>
    [s.pregnancy_risk, s.fertility_risk, s.lactation_risk].some((r) => r === "High Risk")
  );

  if (highRiskSubstances.length === 0) return null;

  const withAlternatives = highRiskSubstances
    .map((s) => ({ substance: s, alternatives: getAlternatives(s.substance_name) }))
    .filter((x) => x.alternatives !== null);

  if (withAlternatives.length === 0) return null;

  return (
    <section className="med-card p-6 mb-6 animate-slide-up">
      <h2 className="section-title">
        <span className="section-icon bg-rose-50 text-rose-700">
          <Lightbulb className="w-4 h-4" />
        </span>
        Safer Alternatives
      </h2>
      <p className="text-xs text-neutral-400 mb-5">
        Recommended substitutions for high-risk substances. Each alternative lists safety
        improvement, experimental compatibility, and known limitations.
      </p>

      <div className="space-y-4">
        {withAlternatives.map(({ substance, alternatives }) => (
          <div key={substance.substance_name} className="border border-neutral-200 rounded-xl overflow-hidden">
            {/* Current substance header */}
            <div className="bg-red-50/50 px-5 py-3 border-b border-red-100">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600" />
                <span className="font-bold text-red-800 text-sm">Current: {substance.substance_name}</span>
              </div>
            </div>

            {/* Alternatives */}
            <div className="divide-y divide-neutral-100">
              {alternatives!.map((alt) => (
                <div key={alt.alternative} className="p-5 bg-rose-50/30">
                  <div className="flex items-center gap-2 mb-3">
                    <Check className="w-4 h-4 text-rose-600" />
                    <span className="font-bold text-rose-800 text-sm">
                      Alternative: {alt.alternative}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                    <div className="bg-white rounded-lg p-3 border border-rose-100">
                      <p className="text-2xs font-semibold text-rose-600 uppercase tracking-wider mb-1">Safety Improvement</p>
                      <p className="text-neutral-700">{alt.improvement}</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-rose-100">
                      <p className="text-2xs font-semibold text-rose-600 uppercase tracking-wider mb-1">Compatibility</p>
                      <p className="text-neutral-700">{alt.compatibility}</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-rose-100">
                      <p className="text-2xs font-semibold text-rose-600 uppercase tracking-wider mb-1">Limitations</p>
                      <p className="text-neutral-700">{alt.limitations}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <p className="text-2xs text-neutral-400 mt-4 flex items-start gap-1.5">
        <span>•</span>
        Always validate alternative protocols with your specific experimental conditions before full adoption.
      </p>
    </section>
  );
}
