"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { FileSearch, Database, FileBarChart, CheckCircle2, AlertCircle, Clock, ArrowLeft } from "lucide-react";
import { pollAnalysisStatus, getAnalysisStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

const phases = [
  { key: "extraction", icon: FileSearch, label: "Extracting chemicals from protocol" },
  { key: "matching", icon: Database, label: "Matching against risk database" },
  { key: "generation", icon: FileBarChart, label: "Generating safety report" },
  { key: "done", icon: CheckCircle2, label: "Report ready" },
];

export default function AnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = Number(params.id);

  const [status, setStatus] = useState<string>("processing");
  const [progress, setProgress] = useState<string>("Initializing analysis...");
  const [elapsed, setElapsed] = useState(0);
  const [currentPhase, setCurrentPhase] = useState(0);
  const abortRef = useRef<(() => void) | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const phaseTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanup = useCallback(() => {
    abortRef.current?.();
    abortRef.current = null;
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (phaseTimerRef.current) { clearInterval(phaseTimerRef.current); phaseTimerRef.current = null; }
  }, []);

  useEffect(() => {
    if (!reportId || isNaN(reportId)) return;

    timerRef.current = setInterval(() => setElapsed((prev) => prev + 1), 1000);
    phaseTimerRef.current = setInterval(() => {
      setCurrentPhase((prev) => Math.min(prev + 1, phases.length - 1));
    }, 3500);

    getAnalysisStatus(reportId)
      .then((s) => {
        if (s.status === "completed") {
          setCurrentPhase(phases.length - 1);
          if (phaseTimerRef.current) clearInterval(phaseTimerRef.current);
          cleanup();
          setTimeout(() => router.push(`/report/${reportId}`), 1000);
          return;
        }
        if (s.status === "failed") {
          if (phaseTimerRef.current) clearInterval(phaseTimerRef.current);
          cleanup();
          setStatus("failed");
          setProgress(s.progress || "Analysis failed");
          return;
        }
        setStatus(s.status);
        setProgress(s.progress);

        abortRef.current = pollAnalysisStatus(
          reportId,
          (update) => { setStatus(update.status); setProgress(update.progress); },
          () => {
            setCurrentPhase(phases.length - 1);
            if (phaseTimerRef.current) clearInterval(phaseTimerRef.current);
            cleanup();
            setTimeout(() => router.push(`/report/${reportId}`), 1000);
          },
          (err) => {
            if (phaseTimerRef.current) clearInterval(phaseTimerRef.current);
            cleanup();
            setStatus("failed");
            setProgress(err.message);
          },
        );
      })
      .catch((err) => { cleanup(); setStatus("failed"); setProgress(err.message); });

    return cleanup;
  }, [reportId, router, cleanup]);

  const formatElapsed = (s: number) => s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;

  return (
    <div className="max-w-xl mx-auto px-4 py-20">
      {status === "processing" && (
        <div className="med-card p-8 animate-fade-in">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-3 h-3 rounded-full bg-rose-500 animate-pulse" />
            <h2 className="text-lg font-bold text-neutral-900">Analyzing Protocol</h2>
            <span className="text-sm text-neutral-400 ml-auto flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              {formatElapsed(elapsed)}
            </span>
          </div>

          {/* Progress phases */}
          <div className="space-y-1">
            {phases.map((phase, i) => {
              const isActive = i === currentPhase && status === "processing";
              const isDone = i < currentPhase || (i === currentPhase && status !== "processing");
              return (
                <div
                  key={phase.key}
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300",
                    isActive && "bg-rose-50",
                    isDone && "text-neutral-400",
                    i > currentPhase && "opacity-40",
                  )}
                >
                  <div
                    className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center transition-colors",
                      isDone && "bg-sage-100",
                      isActive && "bg-rose-100",
                      !isDone && !isActive && "bg-neutral-100",
                    )}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-sage-600" />
                    ) : isActive ? (
                      <div className="w-4 h-4 border-2 border-rose-500 border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <phase.icon className="w-4 h-4 text-neutral-300" />
                    )}
                  </div>
                  <span
                    className={cn(
                      "text-sm font-medium",
                      isDone && "text-neutral-400 line-through",
                      isActive && "text-rose-700",
                      !isDone && !isActive && "text-neutral-300",
                    )}
                  >
                    {phase.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {status === "failed" && (
        <div className="med-card p-8 text-center animate-fade-in">
          <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-7 h-7 text-red-500" />
          </div>
          <h2 className="text-xl font-bold text-neutral-900 mb-2">Analysis Failed</h2>
          <p className="text-neutral-500 mb-6">{progress}</p>
          <button onClick={() => router.push("/")} className="btn-primary">
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </button>
        </div>
      )}

      {status === "pending" && (
        <div className="med-card p-8 text-center animate-fade-in">
          <div className="w-8 h-8 border-2 border-rose-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-neutral-500">Waiting to start analysis...</p>
        </div>
      )}
    </div>
  );
}
