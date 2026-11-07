/** Typed API client for the Nigehbaan AI backend. */

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type Label = "normal" | "abusive" | "scam";
export type RiskLevel = "low" | "medium" | "high";

export interface Probabilities {
  normal: number;
  abusive: number;
  scam: number;
}

export interface AnalyzeResponse {
  label: Label;
  probabilities: Probabilities;
  rule_flags: string[];
  risk_score: number;
  risk_level: RiskLevel;
  explanation: string;
  flagged_words: string[];
  url_features?: Record<string, string | number | boolean> | null;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `Request failed (${res.status})`);
  }

  return res.json() as Promise<T>;
}

export function analyzeText(text: string): Promise<AnalyzeResponse> {
  return postJson<AnalyzeResponse>("/api/analyze/text", { text });
}

export function analyzeUrl(url: string): Promise<AnalyzeResponse> {
  return postJson<AnalyzeResponse>("/api/analyze/url", { url });
}
