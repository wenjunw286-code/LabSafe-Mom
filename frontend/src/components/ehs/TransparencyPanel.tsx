"use client";

import { BarChart3, CheckCircle2, Database, FileSearch, ListChecks, TriangleAlert } from "lucide-react";
import type { ReportDetail, SubstanceItem } from "@/lib/types";

function sourceLabel(value: string | null | undefined) {
  if (!value) return "untracked";
  if (value === "legacy_db") return "local curated KB";
  if (value === "supplemental_kb") return "supplemental KB";
  return value;
}

function topSubstances(substances: SubstanceItem[]) {
  return substances
    .filter((substance) => (substance.fired_rules?.length || 0) > 0 || substance.evidence?.length)
    .slice(0, 6);
}

export default function TransparencyPanel({ report }: { report: ReportDetail }) {
  const metadata = report._v3?.metadata || report.metadata;
  const evidenceSummary = report._v3?.evidence_summary || report.evidence_summary;
  const substances = report.identified_hazardous_materials || [];
  const qc = metadata?.qc;
  const stats = qc?.stats;
  const ai = metadata?.ai;

  return (
    <section className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <div className="med-card p-4">
          <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">QC status</p>
          <div className="mt-2 flex items-center gap-2">
            {qc?.passed ? <CheckCircle2 className="h-5 w-5 text-sage-700" /> : <TriangleAlert className="h-5 w-5 text-amber-700" />}
            <span className="font-bold text-neutral-900">{qc?.passed ? "Passed" : "Review"}</span>
          </div>
        </div>
        <div className="med-card p-4">
          <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">Confidence</p>
          <p className="mt-2 text-xl font-bold text-neutral-900">{Math.round((qc?.confidence_score || 0) * 100)}%</p>
        </div>
        <div className="med-card p-4">
          <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">Resolved</p>
          <p className="mt-2 text-xl font-bold text-neutral-900">{stats?.resolved_count ?? "-"}/{stats?.normalized_count ?? "-"}</p>
        </div>
        <div className="med-card p-4">
          <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">Analysis mode</p>
          <p className="mt-2 text-xl font-bold text-neutral-900 capitalize">{ai?.mode || metadata?.pipeline?.extraction?.analysis_mode || "basic"}</p>
        </div>
      </div>

      <div className="med-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <ListChecks className="h-4 w-4 text-rose-700" />
          <h3 className="font-bold text-neutral-900">AI usage</h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
          <div className="rounded-lg bg-neutral-50 p-3">
            <span className="block text-xs font-semibold uppercase tracking-widest text-neutral-400">Mode</span>
            <span className="mt-1 block font-semibold text-neutral-800 capitalize">{ai?.mode || "basic"}</span>
          </div>
          <div className="rounded-lg bg-neutral-50 p-3">
            <span className="block text-xs font-semibold uppercase tracking-widest text-neutral-400">LLM extraction</span>
            <span className="mt-1 block font-semibold text-neutral-800">{ai?.llm_extraction_enabled ? "Enabled" : "Disabled"}</span>
          </div>
          <div className="rounded-lg bg-neutral-50 p-3">
            <span className="block text-xs font-semibold uppercase tracking-widest text-neutral-400">LLM summary</span>
            <span className="mt-1 block font-semibold text-neutral-800">{ai?.llm_summary_used ? "Used" : "Not used"}</span>
          </div>
        </div>
      </div>

      {(qc?.issues?.length || qc?.warnings?.length) ? (
        <div className="med-card border-l-[3px] border-l-amber-400 p-4">
          <div className="flex items-center gap-2 mb-3">
            <TriangleAlert className="h-4 w-4 text-amber-700" />
            <h3 className="font-bold text-neutral-900">Manual review flags</h3>
          </div>
          <ul className="space-y-2 text-sm text-neutral-700">
            {[...(qc?.issues || []), ...(qc?.warnings || [])].map((item) => (
              <li key={item} className="rounded-lg bg-amber-50 p-3">{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="med-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Database className="h-4 w-4 text-rose-700" />
          <h3 className="font-bold text-neutral-900">Identification provenance</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
          {substances.map((substance) => (
            <div key={`${substance.substance_name}-${substance.cas_number || ""}`} className="rounded-lg border border-neutral-100 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-neutral-800">{substance.substance_name}</span>
                <span className="tag bg-rose-50 text-rose-700 border border-rose-200">{sourceLabel(substance.data_source)}</span>
              </div>
              <p className="mt-1 text-xs text-neutral-400">
                {substance.cas_number ? `CAS ${substance.cas_number}` : "No CAS in report"} · evidence {substance.evidence_level || "D"}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="med-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <ListChecks className="h-4 w-4 text-rose-700" />
          <h3 className="font-bold text-neutral-900">Rule and evidence audit</h3>
        </div>
        <div className="space-y-3">
          {topSubstances(substances).map((substance) => (
            <div key={`${substance.substance_name}-audit`} className="rounded-xl bg-neutral-50 p-3">
              <p className="font-semibold text-neutral-900">{substance.substance_name}</p>
              <div className="mt-2 space-y-1 text-sm text-neutral-600">
                {(substance.fired_rules || []).slice(0, 3).map((rule) => (
                  <p key={`${rule.rule_id}-${rule.population}`}>+{rule.score_contribution} {rule.population}: {rule.reason}</p>
                ))}
              </div>
              {substance.evidence?.length ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {substance.evidence.slice(0, 4).map((item) => (
                    <span key={`${item.source_organization}-${item.claim}`} className="evidence-tag">
                      {item.source_organization}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      <div className="med-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <FileSearch className="h-4 w-4 text-rose-700" />
          <h3 className="font-bold text-neutral-900">Evidence summary</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {(evidenceSummary?.sources_used || []).map((source) => (
            <span key={source} className="evidence-tag">{source}</span>
          ))}
          {!evidenceSummary?.sources_used?.length && <span className="text-sm text-neutral-400">No evidence sources listed.</span>}
        </div>
        <div className="mt-3 flex items-center gap-2 text-sm text-neutral-500">
          <BarChart3 className="h-4 w-4" />
          <span>{evidenceSummary?.total_citations || 0} citations attached to this report.</span>
        </div>
      </div>
    </section>
  );
}
