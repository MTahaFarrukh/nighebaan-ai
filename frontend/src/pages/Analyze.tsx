import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { analyzeText, analyzeUrl, type AnalyzeResponse } from "../api";
import FileAnalyze from "../components/FileAnalyze";
import ResultCard from "../components/ResultCard";
import { Empty, ErrorNotice, PageHeader } from "../components/ui";

export default function Analyze() {
  const [mode, setMode] = useState<"text" | "url" | "file">("text");
  const [input, setInput] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const queries = useQueryClient();
  useEffect(() => () => controller.current?.abort(), []);
  function changeMode(next: "text" | "url" | "file") {
    setMode(next);
    setInput("");
    setResult(null);
    setError("");
  }
  async function analyze() {
    if (!input.trim()) {
      setError("Enter a message or URL first.");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    const active = new AbortController();
    controller.current = active;
    const start = performance.now();
    try {
      const data = await (mode === "text"
        ? analyzeText(input.trim(), active.signal)
        : analyzeUrl(input.trim(), active.signal));
      if (!active.signal.aborted) {
        setResult(data);
        setElapsed(Math.round(performance.now() - start));
        void queries.invalidateQueries({ queryKey: ["alerts"] });
      }
    } catch (failure) {
      if (!active.signal.aborted)
        setError(
          failure instanceof Error && failure.name !== "TypeError"
            ? failure.message
            : "Cannot reach the backend. Check that it is running, then retry.",
        );
    } finally {
      if (!active.signal.aborted) setBusy(false);
    }
  }
  if (mode === "file")
    return (
      <>
        <PageHeader
          eyebrow="MEDIA ANALYSIS"
          title="Read the warning signs."
          description="Extract text from files and check it with the same risk engine."
        />
        <button className="secondary" onClick={() => changeMode("text")}>
          ← Message / URL analysis
        </button>
        <FileAnalyze />
      </>
    );
  return (
    <>
      <PageHeader
        eyebrow="YOUR DIGITAL LOOKOUT"
        title="Check before you trust."
        description="Look for scam, phishing and abusive language in Roman Urdu messages."
      />
      <div className="analysis-layout">
        <div>
          <section className="panel">
            <div className="tabs" aria-label="Input type">
              <button
                disabled={busy}
                className={mode === "text" ? "selected" : ""}
                aria-pressed={mode === "text"}
                onClick={() => changeMode("text")}
              >
                Message text
              </button>
              <button
                disabled={busy}
                className={mode === "url" ? "selected" : ""}
                aria-pressed={mode === "url"}
                onClick={() => changeMode("url")}
              >
                Website URL
              </button>
              <button disabled={busy} onClick={() => changeMode("file")}>
                File upload
              </button>
            </div>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void analyze();
              }}
            >
              <label htmlFor="analysis-input">
                {mode === "text" ? "Paste a message" : "Enter a URL"}
              </label>
              <textarea
                id="analysis-input"
                rows={7}
                value={input}
                disabled={busy}
                onChange={(event) => {
                  setInput(event.target.value);
                  setResult(null);
                }}
                placeholder={
                  mode === "text"
                    ? "Yahan message paste karein…"
                    : "https://example.com"
                }
                spellCheck={false}
                autoComplete="off"
              />
              <div className="row between">
                <small className="muted">
                  Input stays out of saved history.
                </small>
                <button
                  type="button"
                  className="text-button"
                  disabled={busy}
                  onClick={() => {
                    setInput("");
                    setResult(null);
                    setError("");
                  }}
                >
                  Clear
                </button>
              </div>
              <button
                className="primary analyze-button"
                disabled={busy || !input.trim()}
                type="submit"
              >
                {busy ? "Analyzing…" : "Analyze risk"}{" "}
                <span aria-hidden="true">↗</span>
              </button>
            </form>
            {error && <ErrorNotice message={error} />}
            {busy && (
              <p role="status" className="small muted">
                Checking model predictions and expert rules…
              </p>
            )}
            {mode === "text" && (
              <div className="examples">
                <p className="eyebrow">TRY A SYNTHETIC EXAMPLE</p>
                {[
                  "Kal class kitne bajay hai?",
                  "Foran OTP bhejo https://example.com",
                  "Never share your OTP.",
                ].map((value) => (
                  <button
                    key={value}
                    disabled={busy}
                    onClick={() => {
                      setInput(value);
                      setResult(null);
                      setError("");
                    }}
                  >
                    {value}
                  </button>
                ))}
              </div>
            )}
          </section>
          <div className="notice">
            Experimental models. URL false positives are known; even a safe
            placeholder may receive high risk.
          </div>
        </div>
        <aside>
          {result ? (
            <ResultCard result={result} elapsed={elapsed} />
          ) : (
            <section className="panel result-placeholder">
              <Empty title="A little context. A clearer decision.">
                Your risk level, matched rules and explanation will appear here
                after analysis.
              </Empty>
              <div className="legend">
                <span className="badge low">Low</span>
                <span className="badge medium">Medium</span>
                <span className="badge high">High</span>
              </div>
            </section>
          )}
          <p className="privacy-note">
            No message text, phone numbers or URLs are saved. High-risk result
            metadata appears in Dashboard.
          </p>
        </aside>
      </div>
    </>
  );
}
