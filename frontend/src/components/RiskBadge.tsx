import { cn } from "@/lib/utils";

type RiskLevel = "Safe" | "Low Risk" | "Moderate Risk" | "High Risk" | "Unknown";

const styles: Record<RiskLevel, string> = {
  Safe: "risk-safe",
  "Low Risk": "risk-low",
  "Moderate Risk": "risk-moderate",
  "High Risk": "risk-high",
  Unknown: "risk-unknown",
};

export default function RiskBadge({ level }: { level: string }) {
  const style = styles[level as RiskLevel] || styles.Unknown;
  return <span className={cn("risk-badge text-xs", style)}>{level}</span>;
}
