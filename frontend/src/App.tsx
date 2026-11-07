import { useState, type ReactNode } from "react";
import {
  analyzeText,
  analyzeUrl,
  type AnalyzeResponse,
  type RiskLevel,
} from "./api";

const LABEL_STYLES: Record<string, string> = {
  normal: "bg-emerald-500/20 text-emerald-300 ring-emerald-500/40",
  abusive: "bg-orange-500/20 text-orange-300 ring-orange-500/40",
  scam: "bg-rose-500/20 text-rose-300 ring-rose-500/40",
};

const RISK_BAR: Record<RiskLevel, string> = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-rose-500",
};

function highlightText(text: string, words: string[]): ReactNode {
  if (!words.length || !text) return text;
  const escaped = words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(re);
  return parts.map((part, i) =>
    words.some((w) => w.toLowerCase() === part.toLowerCase()) ? (
      <mark key={i} className="rounded bg-amber-400/30 px-0.5 text-amber-100">
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

function ResultCard({
  result,
  sourceText,
}: {
  result: AnalyzeResponse;
  sourceText?: string;
}) {
  const pct = Math.round(result.risk_score * 100);

  return (
    <section className="mt-6 rounded-2xl border border-slate-700/80 bg-slate-800/60 p-5 shadow-xl backdrop-blur">
      <div className="flex flex-wrap items-center gap-3">
        <span
          className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold capitalize ring-1 ${LABEL_STYLES[result.label] ?? LABEL_STYLES.normal}`}
        >
          {result.label}
        </span>
        <span className="text-sm text-slate-400">
          Risk: <strong className="capitalize text-slate-200">{result.risk_level}</strong>{" "}
          ({result.risk_score.toFixed(2)})
        </span>
      </div>

      <div className="mt-4">
        <div className="mb-1 flex justify-between text-xs text-slate-400">
          <span>Risk meter</span>
          <span>{pct}%</span>
        </div>
        <div className="h-2.5 overflow-hidden rounded-full bg-slate-700">
          <div
            className={`h-full rounded-full transition-all duration-500 ${RISK_BAR[result.risk_level]}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {result.rule_flags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {result.rule_flags.map((flag) => (
            <span
              key={flag}
              className="rounded-md bg-sky-500/15 px-2.5 py-1 text-xs font-medium text-sky-300 ring-1 ring-sky-500/30"
            >
              {flag}
            </span>
          ))}
        </div>
      )}

      {sourceText && result.flagged_words.length > 0 && (
        <p className="mt-4 text-sm leading-relaxed text-slate-300">
          {highlightText(sourceText, result.flagged_words)}
        </p>
      )}

      <p className="mt-4 text-sm leading-relaxed text-slate-400">{result.explanation}</p>

      {result.url_features && (
        <dl className="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-400 sm:grid-cols-3">
          {Object.entries(result.url_features).map(([k, v]) => (
            <div key={k} className="rounded-lg bg-slate-900/50 px-2 py-1.5">
              <dt className="text-slate-500">{k}</dt>
              <dd className="truncate font-medium text-slate-200">{String(v)}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

export default function App() {
  const [message, setMessage] = useState("");
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [analyzedText, setAnalyzedText] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runText() {
    if (!message.trim()) {
      setError("Enter a message to analyze.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeText(message.trim());
      setResult(data);
      setAnalyzedText(message.trim());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  async function runUrl() {
    if (!url.trim()) {
      setError("Enter a URL to analyze.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeUrl(url.trim());
      setResult(data);
      setAnalyzedText(undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto min-h-screen max-w-2xl px-4 py-10 sm:py-14">
      <header className="mb-8">
        <p className="text-sm font-medium tracking-wide text-sky-400">AIES Project</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Nigehbaan AI
        </h1>
        <p className="mt-2 text-slate-400">
          Detect scam, phishing, and abusive Roman Urdu messages — ML stub + expert rules.
        </p>
      </header>

      <div className="space-y-6 rounded-2xl border border-slate-700/80 bg-slate-800/40 p-5 shadow-xl backdrop-blur sm:p-6">
        <div>
          <label htmlFor="message" className="mb-2 block text-sm font-medium text-slate-300">
            Message text
          </label>
          <textarea
            id="message"
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="e.g. Aap ne lottery jeet gaye! Foran OTP bhejo..."
            className="w-full resize-y rounded-xl border border-slate-600 bg-slate-900/70 px-3 py-2.5 text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/30"
          />
          <button
            type="button"
            onClick={runText}
            disabled={loading}
            className="mt-3 rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Analyzing…" : "Analyze"}
          </button>
        </div>

        <div className="border-t border-slate-700/80 pt-6">
          <label htmlFor="url" className="mb-2 block text-sm font-medium text-slate-300">
            URL
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://bit.ly/example"
              className="flex-1 rounded-xl border border-slate-600 bg-slate-900/70 px-3 py-2.5 text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/30"
            />
            <button
              type="button"
              onClick={runUrl}
              disabled={loading}
              className="rounded-xl border border-slate-500 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-sky-400 hover:text-sky-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Analyze URL
            </button>
          </div>
        </div>
      </div>

      {error && (
        <p className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          {error}
        </p>
      )}

      {result && <ResultCard result={result} sourceText={analyzedText} />}
    </div>
  );
}
