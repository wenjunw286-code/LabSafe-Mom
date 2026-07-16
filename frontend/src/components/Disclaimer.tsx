import { Info } from "lucide-react";

export default function Disclaimer() {
  return (
    <div className="card p-4 mb-6 bg-amber-50/50 border-amber-200">
      <div className="flex items-start gap-2.5">
        <Info className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-amber-800 leading-relaxed">
          This report is for laboratory safety reference only. It does not replace professional
          occupational health consultation. Always consult your physician or institutional safety
          officer before making decisions based on this report.
        </p>
      </div>
    </div>
  );
}
