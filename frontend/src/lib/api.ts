import type { UploadResponse, AnalyzeStatusResponse, ReportDetail, ReportListResponse, SubstanceSearchResponse } from "./types";
import { getClientId } from "./clientId";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Custom error class with HTTP status code */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Base request function with error handling and timeout */
async function request<T>(
  url: string,
  options?: RequestInit & { timeout?: number },
): Promise<T> {
  const controller = new AbortController();
  const timeout = options?.timeout ?? 120_000; // 2 min default
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(`${API_BASE}${url}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "X-Client-Id": getClientId(),
        ...(options?.headers || {}),
      },
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(
        errorBody.detail || errorBody.message || `Request failed: ${res.status}`,
        res.status,
        errorBody,
      );
    }

    return res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("Request timed out", 408);
    }
    throw new ApiError(
      err instanceof Error ? err.message : "Network error",
      0,
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

// ── Upload ──────────────────────────────────────────────────

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<UploadResponse>("/upload", {
    method: "POST",
    body: formData,
    timeout: 60_000,
  });
}

export async function uploadProtocolText(
  title: string,
  text: string,
): Promise<UploadResponse> {
  return request<UploadResponse>("/upload/text", {
    method: "POST",
    body: JSON.stringify({ title, text }),
    headers: { "Content-Type": "application/json" },
    timeout: 60_000,
  });
}

export async function uploadFiles(files: File[]): Promise<{ uploaded: UploadResponse[]; failed: { filename: string; error: string }[] }> {
  const uploaded: UploadResponse[] = [];
  const failed: { filename: string; error: string }[] = [];

  // Upload sequentially to avoid overwhelming the server
  for (const file of files) {
    try {
      const result = await uploadFile(file);
      uploaded.push(result);
    } catch (err) {
      failed.push({
        filename: file.name,
        error: err instanceof Error ? err.message : "Upload failed",
      });
    }
  }

  return { uploaded, failed };
}

// ── Analysis ────────────────────────────────────────────────

export async function triggerAnalysis(
  reportId: number,
  options?: {
    analysis_mode?: "basic" | "enhanced";
    ai_api_key?: string;
    ai_base_url?: string;
    ai_model?: string;
  },
): Promise<{ id: number; status: string }> {
  return request(`/analyze/${reportId}`, {
    method: "POST",
    body: JSON.stringify({
      analysis_mode: options?.analysis_mode || "basic",
      ai_api_key: options?.ai_api_key || undefined,
      ai_base_url: options?.ai_base_url || undefined,
      ai_model: options?.ai_model || undefined,
    }),
    headers: { "Content-Type": "application/json" },
  });
}

export async function getAnalysisStatus(
  reportId: number,
): Promise<AnalyzeStatusResponse> {
  return request(`/analyze/${reportId}/status`);
}

/** Poll analysis status with exponential backoff.
 *
 * Starts at `initialInterval` ms, doubles each poll up to `maxInterval`.
 * Automatically stops when status is "completed" or "failed".
 * Returns an abort function to cancel polling.
 */
export function pollAnalysisStatus(
  reportId: number,
  onUpdate: (status: AnalyzeStatusResponse) => void,
  onComplete: () => void,
  onError: (error: Error) => void,
  options?: {
    initialInterval?: number; // default 2000ms
    maxInterval?: number;     // default 30000ms
    backoffFactor?: number;   // default 1.5
  },
): () => void {
  const initial = options?.initialInterval ?? 2000;
  const max = options?.maxInterval ?? 30000;
  const factor = options?.backoffFactor ?? 1.5;

  let currentInterval = initial;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let aborted = false;

  const poll = async () => {
    if (aborted) return;

    try {
      const status = await getAnalysisStatus(reportId);
      onUpdate(status);

      if (status.status === "completed") {
        onComplete();
        return;
      }
      if (status.status === "failed") {
        onError(new Error(status.progress || "Analysis failed"));
        return;
      }

      // Schedule next poll with exponential backoff
      currentInterval = Math.min(currentInterval * factor, max);
      timeoutId = setTimeout(poll, currentInterval);
    } catch (err) {
      if (!aborted) {
        onError(err instanceof Error ? err : new Error("Polling error"));
      }
    }
  };

  // Start first poll
  timeoutId = setTimeout(poll, currentInterval);

  // Return abort function
  return () => {
    aborted = true;
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
    }
  };
}

// ── Report ──────────────────────────────────────────────────

export async function getReport(reportId: number): Promise<ReportDetail> {
  return request(`/report/${reportId}`);
}

// ── History ─────────────────────────────────────────────────

export async function getReportHistory(
  page: number = 1,
  pageSize: number = 20,
): Promise<ReportListResponse> {
  return request(`/reports?page=${page}&page_size=${pageSize}`);
}

export async function deleteReport(reportId: number): Promise<void> {
  await request(`/report/${reportId}`, { method: "DELETE" });
}

export async function deleteAllReports(): Promise<{ message: string; deleted: number }> {
  return request("/reports", { method: "DELETE" });
}

// ── Substances ──────────────────────────────────────────────

export interface SubstanceSearchParams {
  search?: string;
  category?: string;
  risk?: string;
}

export async function searchSubstances(params: SubstanceSearchParams) {
  const searchParams = new URLSearchParams();
  if (params.search) searchParams.set("search", params.search);
  if (params.category) searchParams.set("category", params.category);
  if (params.risk) searchParams.set("risk", params.risk);

  const qs = searchParams.toString();
  return request<SubstanceSearchResponse>(
    `/substances${qs ? `?${qs}` : ""}`,
  );
}

// ── Health ──────────────────────────────────────────────────

export async function healthCheck(): Promise<{
  status: string;
  service: string;
  version: string;
  database: Record<string, string>;
  cache: Record<string, unknown>;
}> {
  return request("/health");
}
