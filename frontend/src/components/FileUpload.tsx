"use client";

import { useState, useCallback, useRef } from "react";
import { Upload, FileText, File, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

const VALID_EXTENSIONS = ["pdf", "docx", "txt"];
const MAX_SIZE_MB = 50;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

interface FilePreview {
  name: string;
  size: number;
  type: string;
  contentPreview?: string;
}

interface FileUploadProps {
  onUpload: (file: File) => void;
  uploading: boolean;
  error: string | null;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getExtension(filename: string): string {
  return filename.split(".").pop()?.toLowerCase() || "";
}

function isValidFile(file: File): { valid: boolean; reason?: string } {
  const ext = getExtension(file.name);
  if (!ext || !VALID_EXTENSIONS.includes(ext)) {
    return { valid: false, reason: `Unsupported format: .${ext || "unknown"}. Please use PDF, DOCX, or TXT.` };
  }
  if (file.size > MAX_SIZE_BYTES) {
    return { valid: false, reason: `File too large (${formatFileSize(file.size)}). Maximum is ${MAX_SIZE_MB}MB.` };
  }
  if (file.size === 0) {
    return { valid: false, reason: "File is empty." };
  }
  return { valid: true };
}

export default function FileUpload({ onUpload, uploading, error }: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<FilePreview | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setValidationError(null);
      const result = isValidFile(file);
      if (!result.valid) {
        setValidationError(result.reason || "Invalid file");
        return;
      }
      const previewData: FilePreview = { name: file.name, size: file.size, type: getExtension(file.name) };
      if (previewData.type === "txt" && file.size < 100_000) {
        try { previewData.contentPreview = await file.text().then((t) => t.slice(0, 200)); } catch { /* ok */ }
      }
      setPreview(previewData);
      onUpload(file);
    },
    [onUpload],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); setDragOver(true); }, []);
  const handleDragLeave = useCallback((e: React.DragEvent) => { e.preventDefault(); setDragOver(false); }, []);
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <div className="w-full">
      {/* Drop zone */}
      <div
        className={cn(
          "relative border-2 border-dashed rounded-2xl p-8 sm:p-10 text-center cursor-pointer transition-all duration-200",
          dragOver
            ? "border-rose-400 bg-rose-50/50 scale-[1.01] shadow-lg"
            : "border-neutral-200 bg-white hover:border-rose-300 hover:bg-rose-50/30",
          uploading && "opacity-50 pointer-events-none",
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputRef.current?.click(); } }}
        role="button"
        tabIndex={0}
        aria-label="Upload protocol file. Supports PDF, DOCX, and TXT."
      >
        <div className="flex flex-col items-center gap-4">
          <div
            className={cn(
              "w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-200",
              dragOver ? "bg-rose-100 scale-110" : "bg-rose-50",
            )}
          >
            <Upload className={cn("w-6 h-6 transition-colors", dragOver ? "text-rose-500" : "text-rose-400")} />
          </div>
          <div>
            <p className="text-base font-semibold text-neutral-800">
              {uploading ? "Uploading..." : dragOver ? "Drop to upload" : "Upload Protocol"}
            </p>
            <p className="text-sm text-neutral-400 mt-1">
              {uploading ? "Please wait..." : "Drag & drop or click to browse"}
            </p>
          </div>
          <div className="flex gap-2">
            {VALID_EXTENSIONS.map((ext) => (
              <span
                key={ext}
                className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-rose-50 text-rose-600 border border-rose-100"
              >
                .{ext}
              </span>
            ))}
          </div>
        </div>
        <input ref={inputRef} type="file" accept=".pdf,.docx,.txt" onChange={handleFileChange} className="hidden" />
      </div>

      {/* File preview */}
      {preview && (
        <div className="mt-4 med-card p-4 animate-slide-up">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center">
              {preview.type === "pdf" ? (
                <File className="w-5 h-5 text-red-500" />
              ) : preview.type === "docx" ? (
                <FileText className="w-5 h-5 text-medical-500" />
              ) : (
                <FileText className="w-5 h-5 text-neutral-500" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-neutral-800 text-sm truncate">{preview.name}</p>
              <p className="text-xs text-neutral-400">{formatFileSize(preview.size)}</p>
            </div>
            <CheckCircle2 className="w-5 h-5 text-sage-500" />
          </div>
          {preview.contentPreview && (
            <div className="mt-3 p-3 bg-neutral-50 rounded-lg border border-neutral-100 text-xs text-neutral-500 font-mono max-h-24 overflow-y-auto leading-relaxed">
              {preview.contentPreview}
              {preview.contentPreview.length >= 200 && "..."}
            </div>
          )}
        </div>
      )}

      {/* Validation error */}
      {validationError && (
        <div className="mt-4 flex items-start gap-2.5 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm animate-fade-in" role="alert">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Server error */}
      {error && (
        <div className="mt-4 flex items-start gap-2.5 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm animate-fade-in" role="alert">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
