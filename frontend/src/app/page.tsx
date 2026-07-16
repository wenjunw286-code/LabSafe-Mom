"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FlaskConical, Users, ShieldCheck, Check, Microscope, Heart, Stethoscope, FileText, ClipboardPaste } from "lucide-react";
import Image from "next/image";
import FileUpload from "@/components/FileUpload";
import { uploadFile, uploadProtocolText, triggerAnalysis } from "@/lib/api";
import { cn } from "@/lib/utils";

const trustItems = [
  "Protocol-based Risk Analysis",
  "Chemical Hazard Identification",
  "Pregnancy-specific Assessment",
  "Evidence-based Recommendations",
];

const features = [
  {
    icon: FlaskConical,
    title: "Chemical Hazard Analysis",
    description:
      "Identifies reagents, biological agents, dyes, fixatives, solvents, antibiotics, radioactive materials, and anesthetics from your protocol text.",
  },
  {
    icon: Users,
    title: "Population-specific Risk",
    description:
      "Separate assessments for pregnancy, trying to conceive, and breastfeeding — risk levels adjusted for physiological sensitivity.",
  },
  {
    icon: ShieldCheck,
    title: "Safety Recommendations",
    description:
      "Engineering controls, PPE checklists, and safer chemical alternatives based on NIOSH, OSHA, GHS, and CDC reproductive health guidelines.",
  },
];

const riskLevels = [
  { level: "Critical", color: "bg-red-50 text-red-800 border-red-200", dot: "bg-red-500" },
  { level: "High", color: "bg-orange-50 text-orange-800 border-orange-200", dot: "bg-orange-500" },
  { level: "Moderate", color: "bg-amber-50 text-amber-800 border-amber-200", dot: "bg-amber-500" },
  { level: "Low", color: "bg-sage-50 text-sage-700 border-sage-200", dot: "bg-sage-500" },
];

export default function HomePage() {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"file" | "text">("file");
  const [protocolTitle, setProtocolTitle] = useState("pasted_protocol");
  const [protocolText, setProtocolText] = useState("");

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const uploadRes = await uploadFile(file);
      await triggerAnalysis(uploadRes.id);
      router.push(`/analysis/${uploadRes.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setUploading(false);
    }
  };

  const handleTextSubmit = async () => {
    if (protocolText.trim().length < 20) {
      setError("Please paste a protocol with at least 20 characters.");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const uploadRes = await uploadProtocolText(protocolTitle, protocolText);
      await triggerAnalysis(uploadRes.id);
      router.push(`/analysis/${uploadRes.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Text submission failed");
      setUploading(false);
    }
  };

  return (
    <div className="bg-cream-50">
      {/* ── Hero Section ──────────────────────────── */}
      <section className="relative overflow-hidden bg-white">
        {/* Decorative background layer */}
        <div className="absolute inset-0 pointer-events-none">
          {/* Soft rose glow top-right */}
          <div className="absolute -top-40 -right-40 w-[500px] h-[500px] rounded-full bg-rose-100/20 blur-3xl" />
          {/* Soft sage glow bottom-left */}
          <div className="absolute -bottom-20 -left-20 w-[350px] h-[350px] rounded-full bg-sage-100/20 blur-3xl" />
          {/* Subtle dot grid */}
          <div className="absolute inset-0 opacity-[0.025]"
            style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, #E88BA7 1px, transparent 0)', backgroundSize: '32px 32px' }} />
        </div>

        <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-14 sm:pt-20 pb-10 sm:pb-16 relative">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16 items-center">
            {/* ── Left Column: Text + Upload ──────── */}
            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-50 text-rose-700 text-xs font-semibold mb-6 animate-fade-in border border-rose-200">
                <ShieldCheck className="w-3.5 h-3.5" />
                Laboratory Safety Platform
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-neutral-900 mb-4 animate-slide-up leading-[1.08]">
                <span className="text-rose-500">Safety</span> for<br />
                Expecting Researchers<br />
                in the Laboratory
              </h1>

              <p className="text-lg sm:text-xl text-neutral-500 max-w-lg mb-8 animate-slide-up leading-relaxed">
                Evidence-based chemical hazard assessment for scientists during pregnancy,
                conception planning, and breastfeeding. Upload your protocol and get a
                professional EHS safety report.
              </p>

              <div className="max-w-xl animate-slide-up mb-6">
                <div className="med-card p-3">
                  <div className="grid grid-cols-2 gap-2 mb-3">
                    <button
                      type="button"
                      onClick={() => setInputMode("file")}
                      className={cn(
                        "flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors",
                        inputMode === "file" ? "bg-rose-50 text-rose-700" : "text-neutral-500 hover:bg-neutral-50",
                      )}
                    >
                      <FileText className="h-4 w-4" />
                      Upload file
                    </button>
                    <button
                      type="button"
                      onClick={() => setInputMode("text")}
                      className={cn(
                        "flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors",
                        inputMode === "text" ? "bg-rose-50 text-rose-700" : "text-neutral-500 hover:bg-neutral-50",
                      )}
                    >
                      <ClipboardPaste className="h-4 w-4" />
                      Paste protocol
                    </button>
                  </div>

                  {inputMode === "file" ? (
                    <FileUpload onUpload={handleUpload} uploading={uploading} error={error} />
                  ) : (
                    <div className="space-y-3">
                      <input
                        value={protocolTitle}
                        onChange={(event) => setProtocolTitle(event.target.value)}
                        className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-rose-300 focus:ring-2 focus:ring-rose-100"
                        placeholder="Protocol title"
                      />
                      <textarea
                        value={protocolText}
                        onChange={(event) => setProtocolText(event.target.value)}
                        className="min-h-[220px] w-full resize-y rounded-lg border border-neutral-200 px-3 py-2 text-sm leading-relaxed outline-none focus:border-rose-300 focus:ring-2 focus:ring-rose-100"
                        placeholder="Paste your experimental protocol here, including reagents, CAS numbers, operation steps, ventilation conditions, exposure frequency, and pregnancy/trying-to-conceive/breastfeeding status..."
                      />
                      {error && <p className="text-sm text-red-600">{error}</p>}
                      <button
                        type="button"
                        onClick={handleTextSubmit}
                        disabled={uploading}
                        className="btn-primary w-full"
                      >
                        <ShieldCheck className="h-4 w-4" />
                        {uploading ? "Analyzing..." : "Analyze pasted protocol"}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <p className="text-xs text-neutral-400 animate-fade-in">
                PDF · DOCX · TXT &nbsp;·&nbsp; Max 50MB &nbsp;·&nbsp; Your data stays private
              </p>

              <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-2 animate-fade-in">
                {trustItems.map((item) => (
                  <div key={item} className="trust-item">
                    <span className="trust-check">
                      <Check className="w-3 h-3 text-sage-600" />
                    </span>
                    {item}
                  </div>
                ))}
              </div>
            </div>

            {/* ── Right Column: Rich Image Composition ── */}
            <div className="hidden lg:flex items-center justify-center relative">
              {/* Decorative rings behind the image */}
              <div className="absolute w-[380px] h-[380px] rounded-full border-2 border-rose-100/40 animate-float" />
              <div className="absolute w-[310px] h-[310px] rounded-full border border-dashed border-sage-200/40"
                style={{ animation: 'spin 60s linear infinite' }} />
              <div className="absolute w-[240px] h-[240px] rounded-full bg-gradient-to-br from-rose-50/60 to-sage-50/40 blur-sm" />

              {/* Small decorative icons orbiting */}
              <div className="absolute top-4 right-8 w-10 h-10 rounded-xl bg-white shadow-soft border border-rose-100 flex items-center justify-center"
                style={{ animation: 'float 5s ease-in-out infinite' }}>
                <Microscope className="w-5 h-5 text-rose-400" />
              </div>
              <div className="absolute bottom-12 -left-2 w-10 h-10 rounded-xl bg-white shadow-soft border border-sage-100 flex items-center justify-center"
                style={{ animation: 'float 6s ease-in-out 1s infinite' }}>
                <Heart className="w-5 h-5 text-rose-400" />
              </div>
              <div className="absolute top-1/2 -right-4 w-9 h-9 rounded-xl bg-white shadow-soft border border-medical-100 flex items-center justify-center"
                style={{ animation: 'float 5.5s ease-in-out 0.5s infinite' }}>
                <Stethoscope className="w-4 h-4 text-medical-400" />
              </div>

              {/* Main cover image with soft shadow and white border */}
              <div className="relative z-10">
                <div className="absolute -inset-3 rounded-[2rem] bg-gradient-to-br from-rose-100/30 via-white to-sage-100/30 blur-sm" />
                <Image
                  src="/cover.png"
                  alt="Pregnant researcher working safely in a laboratory"
                  width={380}
                  height={380}
                  className="relative object-contain drop-shadow-xl rounded-3xl"
                  priority
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ──────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-18">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-neutral-900 mb-3">
            Comprehensive Safety Assessment
          </h2>
          <p className="text-neutral-500 max-w-lg mx-auto leading-relaxed">
            Powered by a database of 119 laboratory hazards with reproductive toxicity data
            from NIOSH, OSHA, GHS, CDC, and peer-reviewed research.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map(({ icon: Icon, title, description }) => (
            <div key={title} className="med-card p-6 group hover:border-rose-200 transition-colors">
              <div className="w-11 h-11 rounded-xl bg-rose-50 flex items-center justify-center mb-4 group-hover:bg-rose-100 transition-colors">
                <Icon className="w-5 h-5 text-rose-500" />
              </div>
              <h3 className="font-bold text-neutral-900 mb-2">{title}</h3>
              <p className="text-sm text-neutral-500 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Risk Legend ───────────────────────────────── */}
      <section className="max-w-2xl mx-auto px-4 sm:px-6 pb-16">
        <div className="med-card p-5">
          <h3 className="text-sm font-bold text-neutral-800 mb-4 text-center">Risk Classification Levels</h3>
          <div className="flex flex-wrap justify-center gap-2">
            {riskLevels.map(({ level, color, dot }) => (
              <span
                key={level}
                className={cn("inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border", color)}
              >
                <span className={cn("w-2 h-2 rounded-full", dot)} />
                {level}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────── */}
      <footer className="border-t border-neutral-100 bg-white py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center text-xs text-neutral-400">
          <p className="mb-1">
            This tool provides laboratory safety reference only. Always consult your physician or institutional EHS officer.
          </p>
          <p>LabSafe Mom v2.0 · EHS Risk Assessment Platform</p>
        </div>
      </footer>
    </div>
  );
}
