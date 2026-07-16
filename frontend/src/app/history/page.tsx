"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Trash2, FileText, Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { getReportHistory, deleteReport } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ReportItem {
  id: number;
  original_filename: string;
  file_type: string;
  overall_risk: string | null;
  overall_score: number | null;
  status: string;
  created_at: string | null;
}

const statusConfig: Record<string, { label: string; icon: typeof CheckCircle2; color: string }> = {
  completed: { label: "Completed", icon: CheckCircle2, color: "text-sage-600 bg-sage-50" },
  failed: { label: "Failed", icon: XCircle, color: "text-red-600 bg-red-50" },
  processing: { label: "Processing", icon: Loader2, color: "text-rose-600 bg-rose-50" },
  pending: { label: "Pending", icon: Clock, color: "text-neutral-400 bg-neutral-100" },
};

const riskColors: Record<string, string> = {
  High: "text-red-600", Medium: "text-amber-600", Low: "text-sage-600",
};

export default function HistoryPage() {
  const router = useRouter();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [deleting, setDeleting] = useState<number | null>(null);
  const PAGE_SIZE = 20;

  const fetchReports = useCallback(async (p: number) => {
    setLoading(true); setError(null);
    try {
      const r = await getReportHistory(p, PAGE_SIZE);
      setReports(r.items); setTotal(r.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchReports(page); }, [page, fetchReports]);

  const handleDelete = useCallback(async (id: number) => {
    if (!confirm("Delete this report? This action cannot be undone.")) return;
    setDeleting(id);
    try {
      await deleteReport(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
      setTotal((prev) => prev - 1);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    } finally { setDeleting(null); }
  }, []);

  const formatDate = (d: string | null) =>
    d ? new Date(d).toLocaleString("en-US", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "-";

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <main className="max-w-4xl mx-auto px-4 py-6 sm:py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-extrabold text-neutral-900">Analysis History</h1>
          <p className="text-sm text-neutral-400 mt-1">{total} record{total !== 1 ? "s" : ""}</p>
        </div>
        <button onClick={() => router.push("/")} className="btn-secondary text-sm">
          <ArrowLeft className="w-4 h-4" /> New Analysis
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2" role="alert">
          {error}
          <button onClick={() => fetchReports(page)} className="underline ml-2">Retry</button>
        </div>
      )}

      {loading && (
        <div className="text-center py-16">
          <div className="w-8 h-8 border-[3px] border-neutral-200 border-t-rose-500 rounded-full animate-spin mx-auto" />
          <p className="text-neutral-400 mt-4 text-sm">Loading reports...</p>
        </div>
      )}

      {!loading && !error && reports.length === 0 && (
        <div className="med-card p-12 text-center">
          <div className="w-14 h-14 rounded-2xl bg-rose-50 flex items-center justify-center mx-auto mb-4">
            <FileText className="w-7 h-7 text-rose-300" />
          </div>
          <h2 className="text-lg font-semibold text-neutral-600 mb-2">No Reports Yet</h2>
          <p className="text-sm text-neutral-400 mb-6">Upload a protocol to generate your first safety assessment.</p>
          <button onClick={() => router.push("/")} className="btn-primary">Start Analysis</button>
        </div>
      )}

      {!loading && reports.length > 0 && (
        <>
          <div className="space-y-3">
            {reports.map((r) => {
              const cfg = statusConfig[r.status] || statusConfig.pending;
              const Icon = cfg.icon;
              const isDone = r.status === "completed";
              return (
                <div key={r.id} className="med-card p-4 flex flex-col sm:flex-row sm:items-center gap-3 hover:border-rose-200 transition-colors">
                  <div className="flex-1 min-w-0">
                    <button
                      onClick={() => isDone && router.push(`/report/${r.id}`)}
                      disabled={!isDone}
                      className={cn("text-left font-semibold text-neutral-800 truncate block w-full", isDone && "hover:text-rose-500 cursor-pointer")}
                    >
                      {r.original_filename}
                    </button>
                    <p className="text-xs text-neutral-400 mt-0.5">{formatDate(r.created_at)} · {r.file_type?.toUpperCase()}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {r.overall_risk && <span className={cn("text-sm font-bold", riskColors[r.overall_risk] || "text-neutral-500")}>{r.overall_risk}{r.overall_score != null ? ` (${r.overall_score})` : ""}</span>}
                    <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium", cfg.color)}>
                      {Icon === Loader2 ? <Icon className="w-3 h-3 animate-spin" /> : <Icon className="w-3 h-3" />}
                      {cfg.label}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {isDone && (
                      <button onClick={() => router.push(`/report/${r.id}`)} className="btn-ghost text-xs px-3 py-1.5">View</button>
                    )}
                    <button onClick={() => handleDelete(r.id)} disabled={deleting === r.id} className="btn-danger text-xs px-3 py-1.5">
                      <Trash2 className="w-3 h-3" />
                      {deleting === r.id ? "..." : "Delete"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-6">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="btn-secondary text-xs px-3 py-1.5">Prev</button>
              <span className="text-sm text-neutral-400">{page} / {totalPages}</span>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="btn-secondary text-xs px-3 py-1.5">Next</button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
