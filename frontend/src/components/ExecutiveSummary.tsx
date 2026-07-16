import type { ExecutiveSummary as SummaryType } from "@/lib/types";

const riskBars = [
  { key: "high_risk_count" as const, label: "High", color: "bg-risk-high" },
  { key: "moderate_risk_count" as const, label: "Moderate", color: "bg-risk-moderate" },
  { key: "low_risk_count" as const, label: "Low", color: "bg-risk-low" },
  { key: "safe_count" as const, label: "Safe", color: "bg-risk-safe" },
];

export default function ExecutiveSummary({
  summary,
  overallRisk,
  overallScore,
}: {
  summary: SummaryType;
  overallRisk: string | null;
  overallScore: number | null;
}) {
  const maxCount = Math.max(1, ...riskBars.map((b) => summary[b.key] ?? 0));
  const riskColor =
    overallRisk === "High"
      ? "text-red-600"
      : overallRisk === "Medium"
        ? "text-amber-600"
        : "text-green-600";
  const riskBg =
    overallRisk === "High"
      ? "bg-red-50 border-red-200"
      : overallRisk === "Medium"
        ? "bg-amber-50 border-amber-200"
        : "bg-green-50 border-green-200";

  return (
    <div className="card p-6 mb-6">
      <h2 className="text-lg font-bold text-surface-900 mb-5">Executive Summary</h2>

      <div className="flex items-center gap-5 mb-6">
        <div className={`w-20 h-20 rounded-2xl border-2 flex items-center justify-center ${riskBg}`}>
          <div className="text-center">
            <span className={`text-2xl font-extrabold ${riskColor}`}>{overallScore ?? "-"}</span>
            <p className="text-[10px] text-surface-400 font-medium mt-0.5">SCORE</p>
          </div>
        </div>
        <div>
          <p className={`text-lg font-bold ${riskColor}`}>{overallRisk ?? "N/A"} Risk</p>
          <p className="text-sm text-surface-500 mt-1">{summary.summary_text}</p>
        </div>
      </div>

      <div className="space-y-3">
        {riskBars.map(({ key, label, color }) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs font-medium text-surface-500 w-20 text-right">{label}</span>
            <div className="flex-1 h-6 bg-surface-100 rounded-lg overflow-hidden">
              <div
                className={`h-full rounded-lg ${color} transition-all duration-700 ease-out`}
                style={{ width: `${((summary[key] ?? 0) / maxCount) * 100}%` }}
              />
            </div>
            <span className="text-sm font-semibold text-surface-700 w-7 tabular-nums">{summary[key] ?? 0}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-surface-400 mt-4">
        {summary.total_substances_found} substances identified across 3 population groups
      </p>
    </div>
  );
}
