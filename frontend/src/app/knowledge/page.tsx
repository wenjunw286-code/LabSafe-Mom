"use client";

import { useEffect, useMemo, useState } from "react";
import { BookOpen, Database, Filter, Search, ShieldAlert } from "lucide-react";
import { searchSubstances } from "@/lib/api";
import type { SubstanceSearchResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const riskFilters = ["", "High Risk", "Moderate Risk", "Low Risk", "Safe"];

function riskClass(risk: string) {
  if (risk.includes("High")) return "bg-red-50 text-red-800 border-red-200";
  if (risk.includes("Moderate")) return "bg-amber-50 text-amber-800 border-amber-200";
  if (risk.includes("Low")) return "bg-sage-50 text-sage-700 border-sage-200";
  if (risk.includes("Safe")) return "bg-sage-50 text-sage-700 border-sage-200";
  return "bg-neutral-50 text-neutral-600 border-neutral-200";
}

function strongestRisk(item: SubstanceSearchResult) {
  const values = [item.pregnancy_risk, item.fertility_risk, item.lactation_risk];
  if (values.some((risk) => risk.includes("High"))) return "High";
  if (values.some((risk) => risk.includes("Moderate"))) return "Moderate";
  if (values.some((risk) => risk.includes("Low"))) return "Low";
  if (values.some((risk) => risk.includes("Safe"))) return "Safe";
  return "Unknown";
}

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("");
  const [items, setItems] = useState<SubstanceSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const handle = window.setTimeout(() => {
      searchSubstances({ search: query, risk })
        .then((data) => {
          if (!cancelled) setItems(data.items);
        })
        .catch((err) => {
          if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load knowledge base");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [query, risk]);

  const stats = useMemo(() => {
    return {
      total: items.length,
      high: items.filter((item) => strongestRisk(item) === "High").length,
      moderate: items.filter((item) => strongestRisk(item) === "Moderate").length,
      safeLow: items.filter((item) => ["Low", "Safe"].includes(strongestRisk(item))).length,
    };
  }, [items]);

  return (
    <main className="min-h-screen bg-cream-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-6">
          <div className="inline-flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 border border-rose-200">
            <Database className="h-3.5 w-3.5" />
            Local reproductive safety knowledge base
          </div>
          <h1 className="mt-3 text-2xl sm:text-3xl font-extrabold text-neutral-900">Knowledge Base</h1>
          <p className="mt-2 max-w-2xl text-sm text-neutral-500 leading-relaxed">
            Search chemical risk entries, CAS identifiers, GHS classifications, population-specific risks,
            and evidence notes used by the deterministic assessment pipeline.
          </p>
        </div>

        <section className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-5">
          <div className="med-card p-4">
            <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">Shown</p>
            <p className="mt-1 text-xl font-bold text-neutral-900">{stats.total}</p>
          </div>
          <div className="med-card p-4">
            <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">High</p>
            <p className="mt-1 text-xl font-bold text-red-800">{stats.high}</p>
          </div>
          <div className="med-card p-4">
            <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">Moderate</p>
            <p className="mt-1 text-xl font-bold text-amber-800">{stats.moderate}</p>
          </div>
          <div className="med-card p-4">
            <p className="text-2xs font-semibold uppercase tracking-widest text-neutral-400">Low/Safe</p>
            <p className="mt-1 text-xl font-bold text-sage-700">{stats.safeLow}</p>
          </div>
        </section>

        <section className="med-card p-4 mb-5">
          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
            <label className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="w-full rounded-lg border border-neutral-200 bg-white pl-9 pr-3 py-2.5 text-sm outline-none focus:border-rose-300 focus:ring-2 focus:ring-rose-100"
                placeholder="Search by chemical name or CAS..."
              />
            </label>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-neutral-400" />
              <select
                value={risk}
                onChange={(event) => setRisk(event.target.value)}
                className="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-rose-300 focus:ring-2 focus:ring-rose-100"
              >
                {riskFilters.map((value) => (
                  <option key={value || "all"} value={value}>{value || "All risks"}</option>
                ))}
              </select>
            </div>
          </div>
        </section>

        {error && (
          <div className="med-card border-l-[3px] border-l-red-500 p-4 mb-5 text-sm text-red-700">
            {error}
          </div>
        )}

        <section className="space-y-3">
          {loading ? (
            <div className="med-card p-8 text-center text-sm text-neutral-400">Loading knowledge base...</div>
          ) : items.length === 0 ? (
            <div className="med-card p-8 text-center text-sm text-neutral-400">No matching substances found.</div>
          ) : (
            items.map((item) => (
              <article key={item.id} className="med-card p-4">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-bold text-neutral-900">{item.chemical_name}</h2>
                      {item.cas_number && <span className="tag bg-neutral-50 text-neutral-600 border border-neutral-200">CAS {item.cas_number}</span>}
                      <span className="tag bg-rose-50 text-rose-700 border border-rose-200">{item.category}</span>
                    </div>
                    {item.ghs_classification && (
                      <p className="mt-2 text-sm text-neutral-600">{item.ghs_classification}</p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {[
                      ["Pregnancy", item.pregnancy_risk],
                      ["Fertility", item.fertility_risk],
                      ["Lactation", item.lactation_risk],
                    ].map(([label, value]) => (
                      <span key={label} className={cn("inline-flex rounded-lg border px-2.5 py-1 text-xs font-semibold", riskClass(value))}>
                        {label}: {value}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-3 text-sm">
                  <div className="rounded-lg bg-neutral-50 p-3">
                    <div className="mb-1 flex items-center gap-1.5 font-semibold text-neutral-800">
                      <ShieldAlert className="h-4 w-4 text-rose-700" />
                      Fetal / pregnancy evidence
                    </div>
                    <p className="text-neutral-600 line-clamp-4">{item.effects_on_fetus || item.hazard_statements || "No specific fetal evidence recorded."}</p>
                  </div>
                  <div className="rounded-lg bg-neutral-50 p-3">
                    <div className="mb-1 flex items-center gap-1.5 font-semibold text-neutral-800">
                      <BookOpen className="h-4 w-4 text-rose-700" />
                      Reproductive evidence
                    </div>
                    <p className="text-neutral-600 line-clamp-4">{item.effects_on_reproduction || "No specific reproductive evidence recorded."}</p>
                  </div>
                  <div className="rounded-lg bg-neutral-50 p-3">
                    <div className="mb-1 flex items-center gap-1.5 font-semibold text-neutral-800">
                      <Database className="h-4 w-4 text-rose-700" />
                      Sources
                    </div>
                    <p className="text-neutral-600 line-clamp-4">{item.references || "Source metadata not listed."}</p>
                  </div>
                </div>
              </article>
            ))
          )}
        </section>
      </div>
    </main>
  );
}

