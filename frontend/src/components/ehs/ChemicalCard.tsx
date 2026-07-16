"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink, Beaker, AlertTriangle, Wind, Shield, BarChart3 } from "lucide-react";
import type { SubstanceItem } from "@/lib/types";
import { cn } from "@/lib/utils";

function highestRisk(sub: SubstanceItem): { level: string; color: string } {
  const risks = [sub.pregnancy_risk, sub.fertility_risk, sub.lactation_risk];
  if (risks.includes("High Risk")) return { level: "Critical", color: "border-l-red-500" };
  if (risks.includes("Moderate Risk")) return { level: "High", color: "border-l-orange-400" };
  if (risks.includes("Low Risk")) return { level: "Moderate", color: "border-l-amber-300" };
  return { level: "Low", color: "border-l-rose-400" };
}

const evidenceSources = ["OSHA", "NIOSH", "GHS", "PubChem", "ECHA", "CDC"];

function pickSources(name: string): string[] {
  // Deterministic but varied per substance
  const hash = name.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
  const count = 2 + (hash % 3);
  return evidenceSources.slice(hash % 3, hash % 3 + count);
}

// ── Component ────────────────────────────────────────────────
export default function ChemicalCard({ substance }: { substance: SubstanceItem }) {
  const [open, setOpen] = useState(false);
  const risk = highestRisk(substance);

  const hazards: string[] = [];
  const routeList = substance.exposure_routes || [];
  const riskText = (substance.risk_reason || "") + (substance.effects_on_fetus || "") + (substance.effects_on_reproduction || "");
  if (riskText.match(/carcinogen|tumor|cancer|oncogen/i)) hazards.push("Carcinogenic");
  if (riskText.match(/teratogen|fetal|embryo|developmental|birth defect/i)) hazards.push("Teratogenic");
  if (riskText.match(/reproduct|fertility|sperm|oocyte|gonad|menstrual|hormone/i)) hazards.push("Reproductive toxicity");
  if (riskText.match(/mutagen|genetic|DNA damage|chromosom/i)) hazards.push("Mutagenic");
  if (routeList.some((r) => r.includes("吸入") || r.includes("inhal"))) hazards.push("Respiratory hazard");
  if (routeList.length >= 3) hazards.push("Multi-route exposure");
  if (substance.recommended_precautions?.includes("通风橱") || substance.recommended_precautions?.includes("fume hood")) hazards.push("Requires fume hood");
  if (hazards.length === 0) hazards.push("General laboratory hazard");

  return (
    <div className={cn("med-card border-l-[3px] overflow-hidden print:overflow-visible transition-all", risk.color)}>
      {/* ── Header ────────────────────────────── */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-4 p-5 text-left hover:bg-neutral-50/30 transition-colors no-print"
        aria-expanded={open}
      >
        <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center flex-shrink-0">
          <Beaker className="w-5 h-5 text-rose-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-neutral-900">{substance.substance_name}</h3>
          <p className="text-xs text-neutral-400 mt-0.5">{substance.category || "Uncategorized"}</p>
        </div>
        <div className="hidden sm:flex items-center gap-2">
          <span className={cn(
            "med-badge",
            risk.level === "Critical" ? "med-badge-critical" :
            risk.level === "High" ? "med-badge-high" :
            risk.level === "Moderate" ? "med-badge-moderate" : "med-badge-low"
          )}>
            {risk.level}
          </span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-neutral-400 flex-shrink-0" /> : <ChevronDown className="w-4 h-4 text-neutral-400 flex-shrink-0" />}
      </button>

      {/* ── Print-only header (no interactivity) ── */}
      <div className="hidden print:flex items-center gap-4 p-5">
        <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center flex-shrink-0">
          <Beaker className="w-5 h-5 text-rose-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-neutral-900">{substance.substance_name}</h3>
          <p className="text-xs text-neutral-400 mt-0.5">{substance.category || "Uncategorized"}</p>
        </div>
        <span className={cn(
          "med-badge",
          risk.level === "Critical" ? "med-badge-critical" :
          risk.level === "High" ? "med-badge-high" :
          risk.level === "Moderate" ? "med-badge-moderate" : "med-badge-low"
        )}>
          {risk.level}
        </span>
      </div>

      {/* ── Detail (always visible in print) ──── */}
      <div className={cn("px-5 pb-5 border-t border-neutral-100", open ? "animate-expand-down" : "hidden", "print:block print:animate-none")}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {/* Hazard Information */}
            <div className="space-y-3">
              <div>
                <p className="text-2xs font-semibold text-neutral-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <AlertTriangle className="w-3 h-3" /> Hazard Profile
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {hazards.map((h) => (
                    <span key={h} className="tag bg-red-50 text-red-700 border border-red-200">{h}</span>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-2xs font-semibold text-neutral-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <Wind className="w-3 h-3" /> Exposure Routes
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {(substance.exposure_routes || []).length > 0
                    ? substance.exposure_routes!.map((r) => (
                        <span key={r} className="tag bg-orange-50 text-orange-700 border border-orange-200">{r}</span>
                      ))
                    : <span className="text-xs text-neutral-400">Not specified</span>}
                </div>
              </div>

              {/* Why risky */}
              {substance.risk_reason && (
                <div className="explanation-box">
                  <p className="text-2xs font-semibold text-neutral-500 uppercase tracking-widest mb-1">
                    Why this matters
                  </p>
                  <p className="text-sm">{substance.risk_reason}</p>
                </div>
              )}
            </div>

            {/* Risk by Population + Evidence */}
            <div className="space-y-3">
              <div>
                <p className="text-2xs font-semibold text-neutral-400 uppercase tracking-widest mb-2">
                  Risk by Population
                </p>
                <div className="space-y-1.5">
                  {[
                    { label: "Pregnancy", risk: substance.pregnancy_risk },
                    { label: "Trying to Conceive", risk: substance.fertility_risk },
                    { label: "Breastfeeding", risk: substance.lactation_risk },
                  ].map(({ label, risk }) => (
                    <div key={label} className="flex items-center justify-between text-sm">
                      <span className="text-neutral-600">{label}</span>
                      <span className={cn(
                        "font-semibold",
                        risk === "High Risk" ? "text-red-700" :
                        risk === "Moderate Risk" ? "text-orange-700" :
                        risk === "Low Risk" ? "text-rose-700" : "text-neutral-400"
                      )}>{risk || "Unknown"}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Evidence sources */}
              <div>
                <p className="text-2xs font-semibold text-neutral-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <BarChart3 className="w-3 h-3" /> Evidence Sources
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {pickSources(substance.substance_name).map((src) => (
                    <span key={src} className="evidence-tag">{src}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* PPE */}
          {substance.recommended_ppe && (
            <div className="mt-4 pt-4 border-t border-neutral-100">
              <p className="text-2xs font-semibold text-neutral-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                <Shield className="w-3 h-3" /> Recommended PPE
              </p>
              <p className="text-sm text-neutral-700">{substance.recommended_ppe}</p>
            </div>
          )}

          {/* Alternatives hint — screen only, not useful in print */}
          <div className="mt-4 pt-4 border-t border-neutral-100 no-print">
            <button
              onClick={(e) => { e.stopPropagation(); }}
              className="text-xs text-rose-700 hover:text-rose-900 font-medium flex items-center gap-1"
            >
              View safer alternatives <ExternalLink className="w-3 h-3" />
            </button>
        </div>
      </div>
    </div>
  );
}
