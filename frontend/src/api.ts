import type { components } from "./generated/api";
export type AnalyzeResponse = components["schemas"]["AnalyzeResponse"];
export type FileAnalyzeResponse = components["schemas"]["FileAnalyzeResponse"];
export type RiskLevel = AnalyzeResponse["risk_level"];
export type ModelMetric = components["schemas"]["ModelMetric"];
export type ModelMetrics = components["schemas"]["ModelMetrics"];
export type AlertHistory = components["schemas"]["AlertHistory"];
export type PublicSettings = components["schemas"]["PublicSettings"];
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  init: RequestInit = {},
  timeout = 30000,
): Promise<T> {
  const response = await fetch(`${API_BASE}/api${path}`, {
    ...init,
    cache: "no-store",
    signal: init.signal
      ? AbortSignal.any([init.signal, AbortSignal.timeout(timeout)])
      : AbortSignal.timeout(timeout),
  });
  if (!response.ok) {
    // Do not echo validation payloads: they can contain the submitted input.
    throw new Error(
      response.status === 413
        ? "File exceeds the upload, page, duration or pixel limit."
        : response.status === 415
          ? "Unsupported file type or mismatched contents. Use PDF, PNG/JPEG/WebP, audio or MP4/WebM."
          : response.status === 429
            ? "Another media file is being processed. Retry shortly."
            : response.status === 422
              ? path === "/analyze/file"
                ? "The file could not be analyzed. Try a clearer, unencrypted file containing readable text or speech."
                : "Check your input and try again."
              : response.status === 503
                ? "This service is temporarily unavailable. Check the local backend and model files."
                : `Request failed (${response.status}). Please try again.`,
    );
  }
  return response.json() as Promise<T>;
}
export const analyzeText = (text: string, signal?: AbortSignal) =>
  request<AnalyzeResponse>("/analyze/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
export const analyzeUrl = (url: string, signal?: AbortSignal) =>
  request<AnalyzeResponse>("/analyze/url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
    signal,
  });
export const getMetrics = (signal?: AbortSignal) =>
  request<ModelMetrics>("/metrics/models", { signal });
export const getAlerts = (offset: number, signal?: AbortSignal) =>
  request<AlertHistory>(`/alerts?limit=20&offset=${offset}`, { signal });
export const getSettings = (signal?: AbortSignal) =>
  request<PublicSettings>("/settings", { signal });

export const analyzeFile = (file: File, signal?: AbortSignal) => {
  const body = new FormData();
  body.append("file", file);
  return request<FileAnalyzeResponse>(
    "/analyze/file",
    { method: "POST", body, signal },
    300000,
  );
};

export const simulateWhatsApp = () =>
  request<components["schemas"]["Decision"]>("/simulate/whatsapp", { method: "POST" });

export const getWhatsAppPairing = (signal?: AbortSignal) =>
  request<components["schemas"]["PairingStatus"]>("/whatsapp/pairing", {
    headers: { "X-Nigehbaan-Settings": "1" },
    signal,
  });
