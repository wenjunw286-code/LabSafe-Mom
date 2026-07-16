import { AlertTriangle } from "lucide-react";
import type { HighRiskItem as HRItem } from "@/lib/types";
import RiskBadge from "./RiskBadge";

export default function HighRiskItems({ items }: { items: HRItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="mb-6">
      <h2 className="text-lg font-bold text-surface-900 mb-4 flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-red-500" />
        High-Risk Items
      </h2>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.substance_name} className="card border-l-4 border-l-red-400 p-4 bg-red-50/30">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h3 className="font-bold text-surface-900">{item.substance_name}</h3>
                <p className="text-xs text-surface-400">{item.category}</p>
              </div>
              <div className="flex items-center gap-1.5 flex-wrap">
                <RiskBadge level={item.pregnancy_risk} />
                <RiskBadge level={item.fertility_risk} />
                <RiskBadge level={item.lactation_risk} />
              </div>
            </div>
            {item.recommended_precautions && (
              <p className="text-sm text-red-700 mt-2 whitespace-pre-line font-medium">
                {item.recommended_precautions}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
