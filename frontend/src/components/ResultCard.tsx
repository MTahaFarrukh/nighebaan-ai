import type { AnalyzeResponse } from "../api";
export default function ResultCard({
  result,
  elapsed,
}: {
  result: AnalyzeResponse;
  elapsed: number;
}) {
  const percent = Math.round(result.risk_score * 100);
  return (
    <section
      className="panel result"
      aria-label="Analysis result"
      aria-live="polite"
    >
      <div className="row between">
        <p className="eyebrow">Analysis result</p>
        <small className="muted">{elapsed} ms round trip</small>
      </div>
      <div className="row between">
        <div>
          <span className={`badge ${result.risk_level}`}>
            {result.risk_level} risk
          </span>
          <h2 className="capitalize">{result.label}</h2>
        </div>
        <strong className={`risk-number ${result.risk_level}`}>
          {percent}
          <small>/100</small>
        </strong>
      </div>
      <div
        className="risk-track"
        role="meter"
        aria-label="Risk score"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
      >
        <div className={result.risk_level} style={{ width: `${percent}%` }} />
      </div>
      <h3>Why this result?</h3>
      <p className="explanation">{result.explanation}</p>
      <div className="chips">
        {result.rule_flags.map((flag) => (
          <span key={flag} className="chip">
            {flag}
          </span>
        ))}
        {!result.rule_flags.length && (
          <small className="muted">No configured rules matched.</small>
        )}
      </div>
      {result.flagged_words.length > 0 && (
        <p>Flagged language: {result.flagged_words.join(", ")}</p>
      )}
      <details>
        <summary>Model probabilities &amp; URL features</summary>
        <dl className="feature-grid">
          {Object.entries(result.probabilities).map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{(value * 100).toFixed(1)}%</dd>
            </div>
          ))}
          {Object.entries(result.url_features ?? {}).map(([key, value]) => (
            <div key={key}>
              <dt>{key.replaceAll("_", " ")}</dt>
              <dd>
                {typeof value === "number"
                  ? Number(value.toFixed(3))
                  : String(value)}
              </dd>
            </div>
          ))}
        </dl>
      </details>
      <p className="small muted">
        A risk score is a warning signal, not a verdict. Verify requests through
        a trusted channel.
      </p>
    </section>
  );
}
