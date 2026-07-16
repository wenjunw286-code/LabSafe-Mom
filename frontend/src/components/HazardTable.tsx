"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { SubstanceItem } from "@/lib/types";
import RiskBadge from "./RiskBadge";
import { cn } from "@/lib/utils";

export default function HazardTable({ substances }: { substances: SubstanceItem[] }) {
  if (substances.length === 0) {
    return (
      <div className="card p-8 text-center mb-6">
        <p className="text-surface-500">No hazardous substances identified.</p>
      </div>
    );
  }

  return (
    <div className="mb-6">
      <h2 className="text-lg font-bold text-surface-900 mb-4">Identified Hazardous Materials</h2>
      <div className="space-y-3">
        {substances.map((sub) => (
          <HazardCard key={sub.id} substance={sub} />
        ))}
      </div>
    </div>
  );
}

function HazardCard({ substance }: { substance: SubstanceItem }) {
  const [open, setOpen] = useState(false);
  const risks = [substance.pregnancy_risk, substance.fertility_risk, substance.lactation_risk];
  const hasHigh = risks.some((r) => r === "High Risk");
  const borderColor = hasHigh ? "border-l-red-400" : "border-l-brand-400";

  return (
    <div className={cn("card border-l-4 overflow-hidden", borderColor)}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-4 p-4 text-left hover:bg-surface-50/50 transition-colors"
        aria-expanded={open}
      >
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-surface-900 truncate">{substance.substance_name}</h3>
          <p className="text-xs text-surface-400 mt-0.5">{substance.category || "Uncategorized"}</p>
        </div>
        <div className="hidden sm:flex items-center gap-2">
          <RiskBadge level={substance.pregnancy_risk || "Unknown"} />
          <RiskBadge level={substance.fertility_risk || "Unknown"} />
          <RiskBadge level={substance.lactation_risk || "Unknown"} />
        </div>
        {open ? (
          <ChevronUp className="w-4 h-4 text-surface-400 flex-shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-surface-400 flex-shrink-0" />
        )}
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-surface-100 pt-4 animate-fade-in">
          <div className="flex gap-2 mb-4 sm:hidden">
            <div className="text-xs"><span className="text-surface-400">Pregnancy: </span><RiskBadge level={substance.pregnancy_risk || "Unknown"} /></div>
            <div className="text-xs"><span className="text-surface-400">Fertility: </span><RiskBadge level={substance.fertility_risk || "Unknown"} /></div>
            <div className="text-xs"><span className="text-surface-400">Lactation: </span><RiskBadge level={substance.lactation_risk || "Unknown"} /></div>
          </div>
          {substance.risk_reason && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Risk Reason</p>
              <p className="text-sm text-surface-700">{substance.risk_reason}</p>
            </div>
          )}
          {substance.effects_on_fetus && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Effects on Fetus</p>
              <p className="text-sm text-surface-700">{substance.effects_on_fetus}</p>
            </div>
          )}
          {substance.recommended_ppe && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Recommended PPE</p>
              <p className="text-sm text-surface-700">{substance.recommended_ppe}</p>
            </div>
          )}
          {substance.recommended_precautions && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Precautions</p>
              <div className="text-sm text-surface-700 whitespace-pre-line">{substance.recommended_precautions}</div>
            </div>
          )}
          {substance.found_in_section && (
            <div>
              <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Found In Section</p>
              <p className="text-xs text-surface-500 bg-surface-50 rounded-lg p-2.5 font-mono leading-relaxed">
                &ldquo;{substance.found_in_section}&rdquo;
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
