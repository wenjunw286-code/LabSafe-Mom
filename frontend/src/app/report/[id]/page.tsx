"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Printer, FileText, FlaskConical as Flask } from "lucide-react";
import type { ReportDetail } from "@/lib/types";
import { getReport } from "@/lib/api";
import Image from "next/image";
import { RiskDashboard, ChemicalCard, PopulationRisk, ControlChecklist } from "@/components/ehs";
import ActionPlan from "@/components/ehs/ActionPlan";
import TransparencyPanel from "@/components/ehs/TransparencyPanel";
import AlternativesPanel from "@/components/ehs/AlternativesPanel";

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString("en-US", { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function SectionHeader({ number, title }: { number: number; title: string }) {
  return (
    <div className="flex items-center gap-3 mb-4 pb-3 border-b border-neutral-100">
      <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center text-sm font-bold">{number}</span>
      <h2 className="text-lg font-bold text-neutral-900">{title}</h2>
    </div>
  );
}

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = Number(params.id);
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = () => {
    if (!reportId || isNaN(reportId)) return;
    setLoading(true); setError(null);
    getReport(reportId).then((data) => { setReport(data); setLoading(false); }).catch((err) => { setError(err.message); setLoading(false); });
  };

  useEffect(() => { fetchReport(); }, [reportId]);
  const substances = useMemo(() => report?.identified_hazardous_materials || [], [report]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="animate-pulse space-y-4">
          <div className="h-28 bg-neutral-100 rounded-2xl" />
          <div className="h-40 bg-neutral-100 rounded-2xl" />
          <div className="h-48 bg-neutral-100 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <main className="max-w-lg mx-auto px-4 py-20 text-center">
        <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4"><FileText className="w-7 h-7 text-red-400" /></div>
        <h2 className="text-xl font-bold text-neutral-900 mb-2">Unable to Load Report</h2>
        <p className="text-neutral-500 mb-6">{error || "Report not found"}</p>
        <div className="flex justify-center gap-3">
          <button onClick={fetchReport} className="btn-secondary text-sm">Retry</button>
          <button onClick={() => router.push("/")} className="btn-primary text-sm"><ArrowLeft className="w-4 h-4" /> Home</button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-cream-50">
      {/* Top Bar */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-xl border-b border-neutral-100 no-print">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5 min-w-0">
            <Image src="/cover.png" alt="" width={24} height={24} className="rounded-md object-cover flex-shrink-0" />
            <p className="text-sm font-bold text-neutral-900 truncate">LabSafe <span className="text-rose-500">Mom</span></p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 no-print">
            <button onClick={() => router.push("/")} className="btn-secondary text-xs px-3 py-1.5"><ArrowLeft className="w-3.5 h-3.5" /> New</button>
            <button onClick={() => window.print()} className="btn-primary text-xs px-3 py-1.5"><Printer className="w-3.5 h-3.5" /> Print</button>
          </div>
        </div>
      </header>

      {/* Report Body */}
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-8" id="report-content">
        {/* Document title */}
        <div className="mb-7">
          <h1 className="text-xl font-extrabold text-neutral-900 mb-1">Laboratory Safety Assessment Report</h1>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-neutral-400">
            <span className="font-medium text-neutral-600 truncate max-w-[260px]">{report.original_filename}</span>
            <span className="hidden sm:inline">·</span>
            <span>{formatDate(report.created_at)}</span>
          </div>
        </div>

        {/* S1: Risk Overview */}
        <section className="mb-7">
          <SectionHeader number={1} title="Risk Overview" />
          <RiskDashboard report={report} />
        </section>

        {/* S2: Action Plan */}
        <section className="mb-7">
          <SectionHeader number={2} title="Decision & Action Plan" />
          <ActionPlan report={report} />
        </section>

        {/* S3: Chemical Risk Assessment */}
        <section className="mb-7">
          <SectionHeader number={3} title="Chemical Risk Assessment" />
          {substances.length === 0 ? (
            <div className="med-card p-6 text-center"><p className="text-neutral-400 text-sm">No hazardous substances identified.</p></div>
          ) : (
            <div className="space-y-2.5">
              {substances.map((sub) => <ChemicalCard key={sub.id} substance={sub} />)}
            </div>
          )}
        </section>

        {/* S4: Population-Specific Risk */}
        <section className="mb-7">
          <SectionHeader number={4} title="Population-Specific Risk" />
          <PopulationRisk report={report} />
        </section>

        {/* S5: Safety Controls */}
        <section className="mb-7">
          <SectionHeader number={5} title="PPE & Safety Controls" />
          <ControlChecklist substances={substances} />
        </section>

        {/* S6: Safer Alternatives */}
        <section className="mb-7">
          <SectionHeader number={6} title="Safer Alternatives" />
          <AlternativesPanel substances={substances} />
        </section>

        {/* S7: Evidence and QC */}
        <section className="mb-7">
          <SectionHeader number={7} title="Evidence, Rules & QC" />
          <TransparencyPanel report={report} />
        </section>

        {/* Disclaimer */}
        <div className="border border-amber-200 bg-amber-50/50 rounded-2xl p-4 mb-7">
          <div className="flex items-start gap-2.5">
            <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-amber-100 flex items-center justify-center text-amber-600 font-bold text-xs">!</span>
            <div>
              <p className="text-xs font-bold text-amber-800 mb-0.5">Disclaimer</p>
              <p className="text-2xs text-amber-700 leading-relaxed">
                This report is a laboratory safety reference tool. It does not replace professional occupational health consultation or institutional EHS review.
                Always consult your physician or institutional safety officer before making decisions based on this assessment.
              </p>
            </div>
          </div>
        </div>

        <div className="text-center text-2xs text-neutral-300 pb-8 no-print">
          LabSafe Mom · {report.original_filename} · {formatDate(report.created_at)}
        </div>
      </div>
    </main>
  );
}
