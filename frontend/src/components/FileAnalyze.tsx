import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { analyzeFile, getSettings, type FileAnalyzeResponse } from "../api";
import ResultCard from "./ResultCard";
import { Empty, ErrorNotice } from "./ui";

export default function FileAnalyze() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<FileAnalyzeResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement | null>(null);
  const controller = useRef<AbortController | null>(null);
  const queries = useQueryClient();
  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: ({ signal }) => getSettings(signal),
  });
  useEffect(() => () => controller.current?.abort(), []);
  const limit = settings.data?.max_upload_mb ?? 25;
  function choose(next: File | null) {
    setError("");
    setResult(null);
    if (next && next.size > limit * 1024 * 1024) {
      setError(`Choose a file smaller than ${limit} MB.`);
      setFile(null);
      return;
    }
    setFile(next);
  }
  async function run() {
    if (!file) return;
    const active = new AbortController();
    controller.current = active;
    setBusy(true);
    setError("");
    setResult(null);
    const start = performance.now();
    try {
      const response = await analyzeFile(file, active.signal);
      if (!active.signal.aborted) {
        setResult(response);
        setElapsed(Math.round(performance.now() - start));
        void queries.invalidateQueries({ queryKey: ["alerts"] });
      }
    } catch (failure) {
      if (!active.signal.aborted)
        setError(
          failure instanceof Error && failure.name !== "TypeError"
            ? failure.message
            : "Cannot reach the backend. Check the local service and retry.",
        );
    } finally {
      if (!active.signal.aborted) setBusy(false);
    }
  }
  return (
    <div className="analysis-layout mt">
      <div>
        <section className="panel">
          <h2>Analyze a file</h2>
          <p className="muted small">
            Screenshot, PDF, voice note or short video. Processing runs locally
            on the backend.
          </p>
          <div
            className={`drop-zone ${dragging ? "dragging" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              if (!busy) setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              if (!busy) choose(event.dataTransfer.files[0] ?? null);
            }}
          >
            <label htmlFor="media-input">Choose a file or drop it here</label>
            <input
              id="media-input"
              ref={input}
              type="file"
              disabled={busy}
              accept=".pdf,.png,.jpg,.jpeg,.webp,.wav,.mp3,.ogg,.opus,.flac,.m4a,.mp4,.webm"
              onChange={(event) => choose(event.target.files?.[0] ?? null)}
            />
            <p className="small muted">
              {limit} MB maximum · PDFs up to{" "}
              {settings.data?.max_pdf_pages ?? 20} pages · Audio/video up to{" "}
              {settings.data?.max_media_seconds ?? 60} seconds
            </p>
          </div>
          {file && (
            <p className="small file-name">
              {file.name} · {(file.size / 1024).toFixed(0)} KB
            </p>
          )}
          <div className="row between">
            <button
              className="primary"
              disabled={!file || busy}
              onClick={() => void run()}
            >
              {busy ? "Extracting & analyzing…" : "Analyze file"}
            </button>
            <button
              className="text-button"
              disabled={busy}
              onClick={() => {
                choose(null);
                if (input.current) input.current.value = "";
              }}
            >
              Clear
            </button>
          </div>
          {busy && (
            <p className="small muted mt" role="status">
              Local OCR/transcription may take a few minutes. Keep this page
              open.
            </p>
          )}
          {error && <ErrorNotice message={error} />}
          <div className="notice">
            OCR and speech recognition can misread content. Video samples frames
            every 10 seconds. Review the preview before trusting a result.
          </div>
          <p className="small muted">
            Temporary uploads and converted files are deleted after processing,
            including failures. Extracted text is not saved in history.
          </p>
        </section>
      </div>
      <aside>
        {result ? (
          <>
            <ResultCard result={result} elapsed={elapsed} />
            <section className="panel mt">
              <div className="row between">
                <h2>Extraction details</h2>
                <span className="badge neutral">{result.modality}</span>
              </div>
              {result.extraction_confidence != null && (
                <p className="small muted">
                  OCR confidence:{" "}
                  {(result.extraction_confidence * 100).toFixed(1)}% (not model
                  accuracy)
                </p>
              )}
              <ul className="warning-list">
                {(result.warnings ?? []).map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
              <details>
                <summary>Show extracted text · masked preview</summary>
                <pre className="extracted-preview">{result.extracted_text}</pre>
              </details>
            </section>
          </>
        ) : (
          <section className="panel result-placeholder">
            <Empty title="From a file to an explanation.">
              Upload one supported file. Its extracted text will go through the
              same model and expert rules as typed messages.
            </Empty>
          </section>
        )}
      </aside>
    </div>
  );
}
