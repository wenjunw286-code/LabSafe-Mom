import { Shield } from "lucide-react";
import type { PrecautionItem as PItem } from "@/lib/types";

export default function Precautions({ items }: { items: PItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="mb-6">
      <h2 className="text-lg font-bold text-surface-900 mb-4 flex items-center gap-2">
        <Shield className="w-5 h-5 text-brand-600" />
        Recommended Precautions
      </h2>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.substance_name} className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-surface-900">{item.substance_name}</h3>
              <span className="risk-badge text-xs bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20">
                {item.risk}
              </span>
            </div>
            <ul className="space-y-1.5">
              {item.precautions.map((p, i) => (
                <li key={i} className="text-sm text-surface-700 flex items-start gap-2">
                  <span className="text-brand-500 mt-0.5 flex-shrink-0">•</span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
