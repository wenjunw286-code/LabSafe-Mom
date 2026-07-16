"use client";

import { Users, Star } from "lucide-react";
import type { ReportDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

const populationLabels: Record<string, { name: string; icon: string }> = {
  "妊娠期": { name: "Pregnancy", icon: "🤰" },
  "备孕期": { name: "Trying to Conceive", icon: "🤱" },
  "哺乳期": { name: "Breastfeeding", icon: "🍼" },
};

function starRating(risks: { high: number; moderate: number; low: number; safe: number }): number {
  const score = risks.high * 4 + risks.moderate * 2 + risks.low * 1;
  // 0 stars = safe, 5 stars = most risky
  return Math.min(5, Math.ceil(score / 6));
}

function ratingLabel(stars: number): string {
  if (stars >= 5) return "Maximum caution required";
  if (stars >= 4) return "Significant risk — enhanced PPE";
  if (stars >= 3) return "Moderate concern — standard PPE";
  if (stars >= 2) return "Low risk — routine precautions";
  return "Minimal concern";
}

// ── Component ────────────────────────────────────────────────
export default function PopulationRisk({ report }: { report: ReportDetail }) {
  const riskByCategory = report.risk_by_category;
  if (!riskByCategory) return null;

  const populations = Object.entries(riskByCategory);

  return (
    <section className="med-card p-6 mb-6 animate-slide-up">
      <h2 className="section-title">
        <span className="section-icon bg-rose-50 text-rose-700">
          <Users className="w-4 h-4" />
        </span>
        Population-Specific Risk Assessment
      </h2>
      <p className="text-xs text-neutral-400 mb-5">
        Risk levels adjust based on physiological sensitivity. The same chemical may pose different
        risk levels for different populations.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {populations.map(([pop, risks]) => {
          const stars = starRating(risks);
          const info = populationLabels[pop] || { name: pop, icon: "" };

          return (
            <div key={pop} className="bg-neutral-50/80 rounded-xl p-5 border border-neutral-200">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">{info.icon}</span>
                <h3 className="font-bold text-neutral-800 text-sm">{info.name}</h3>
              </div>

              {/* Star rating */}
              <div className="flex items-center gap-0.5 mb-3">
                {[1, 2, 3, 4, 5].map((s) => (
                  <Star
                    key={s}
                    className={cn(
                      "w-4 h-4",
                      s <= stars ? "text-amber-500 fill-amber-500" : "text-neutral-300",
                    )}
                  />
                ))}
              </div>
              <p className="text-xs text-neutral-500 mb-4">{ratingLabel(stars)}</p>

              {/* Risk breakdown */}
              <div className="space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <span className="text-neutral-500">Critical</span>
                  <span className="font-bold text-red-700">{risks.high}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Moderate</span>
                  <span className="font-bold text-amber-700">{risks.moderate}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Low</span>
                  <span className="font-bold text-rose-700">{risks.low}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Safe</span>
                  <span className="font-bold text-green-700">{risks.safe}</span>
                </div>
              </div>

              {/* Sensitivity note */}
              {stars >= 4 && (
                <div className="mt-4 p-3 bg-red-50/60 rounded-lg border border-red-100 text-xs text-red-700">
                  ⚠ This population has heightened sensitivity. Consider protocol modifications.
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
