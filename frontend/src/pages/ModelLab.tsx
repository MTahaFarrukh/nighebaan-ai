import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { getMetrics, type ModelMetric } from "../api";
import { Empty, ErrorNotice, Loading, PageHeader } from "../components/ui";
function Comparison({ rows }: { rows: ModelMetric[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Model / variant</th>
            <th>Macro-F1</th>
            <th>Accuracy</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name}>
              <td>{row.name.replaceAll("_", " ")}</td>
              <td>{row.macro_f1.toFixed(4)}</td>
              <td>
                {row.accuracy == null
                  ? "Not reported"
                  : `${(row.accuracy * 100).toFixed(2)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export default function ModelLab() {
  const query = useQuery({
    queryKey: ["metrics"],
    queryFn: ({ signal }) => getMetrics(signal),
    staleTime: 60000,
  });
  const [kind, setKind] = useState<"text" | "url">("text");
  const [selected, setSelected] = useState("");
  const rows =
    (kind === "text" ? query.data?.models : query.data?.url_models) ?? [];
  const best =
    kind === "text" ? query.data?.best_model : query.data?.best_url_model;
  const model =
    rows.find((row) => row.name === selected) ??
    rows.find((row) => row.name === best) ??
    rows[0];
  const labels =
    kind === "text" ? ["normal", "abusive", "scam"] : ["benign", "phishing"];
  const maxCell = Math.max(1, ...(model?.confusion_matrix ?? []).flat());
  return (
    <>
      <PageHeader
        eyebrow="EVIDENCE, NOT ESTIMATES"
        title="Inside the models."
        description="Measured validation comparisons, confusion matrices and ablations."
      />
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorNotice
          message="Model metrics are unavailable. Start the backend and ensure metrics.json exists."
          retry={() => void query.refetch()}
        />
      ) : (
        <>
          <div className="notice">
            Validation results · Text data is
            human-unverified. URL results are dataset-specific and do not
            establish real-world reliability.
          </div>
          <div className="tabs page-tabs">
            <button
              className={kind === "text" ? "selected" : ""}
              aria-pressed={kind === "text"}
              onClick={() => {
                setKind("text");
                setSelected("");
              }}
            >
              Text models
            </button>
            <button
              className={kind === "url" ? "selected" : ""}
              aria-pressed={kind === "url"}
              onClick={() => {
                setKind("url");
                setSelected("");
              }}
            >
              URL models
            </button>
          </div>
          {!rows.length ? (
            <section className="panel">
              <Empty title="No model results yet.">
                Measured results will appear once training reports are
                available.
              </Empty>
            </section>
          ) : (
            <>
              <section className="panel">
                <div className="row between">
                  <h2>Validation comparison</h2>
                  <span className="badge neutral">
                    Selected: {best?.replaceAll("_", " ") ?? "Not reported"}
                  </span>
                </div>
                <div className="chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={rows}
                      margin={{ left: 0, right: 15, bottom: 10 }}
                    >
                      <CartesianGrid stroke="#263944" vertical={false} />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: "#91a6b2", fontSize: 11 }}
                        interval={0}
                      />
                      <YAxis
                        domain={[0, 1]}
                        tick={{ fill: "#91a6b2", fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#152631",
                          border: "1px solid #38505d",
                          color: "#f3f7f8",
                        }}
                      />
                      <Bar
                        dataKey="macro_f1"
                        name="Macro-F1"
                        fill="#4dd9ba"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <Comparison rows={rows} />
              </section>
              <section className="panel mt">
                <div className="row between">
                  <h2>Where predictions land</h2>
                  <label className="select-label">
                    Model
                    <select
                      value={model?.name ?? ""}
                      onChange={(event) => setSelected(event.target.value)}
                    >
                      {rows.map((row) => (
                        <option key={row.name} value={row.name}>
                          {row.name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <p className="small muted">
                  Rows: actual class · Columns: predicted class · Counts, not
                  percentages
                </p>
                <div className="table-wrap">
                  <table className="matrix">
                    <thead>
                      <tr>
                        <th>Actual / predicted</th>
                        {labels.map((label) => (
                          <th key={label}>{label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {model?.confusion_matrix?.map((row, index) => (
                        <tr key={labels[index]}>
                          <th>{labels[index]}</th>
                          {row.map((value, column) => (
                            <td
                              key={column}
                              style={{
                                background: `rgba(77,217,186,${0.06 + (0.35 * value) / maxCell})`,
                              }}
                            >
                              {value.toLocaleString()}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Class</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(model?.per_class ?? {}).map(
                        ([label, metric]) => (
                          <tr key={label}>
                            <td>{label}</td>
                            <td>{metric.p.toFixed(4)}</td>
                            <td>{metric.r.toFixed(4)}</td>
                            <td>{metric.f1.toFixed(4)}</td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
          {kind === "text" && (
            <section className="panel mt">
              <h2>Ablation experiments</h2>
              <p className="muted small">
                Controlled text variants. Historical ML/rules/hybrid results
                exclude the later URL-model fusion.
              </p>
              {!query.data?.ablations?.length ? (
                <p className="muted">No ablation results available.</p>
              ) : (
                query.data.ablations.map((group) => (
                  <details key={group.name}>
                    <summary>{group.name.replaceAll("_", " ")}</summary>
                    <Comparison rows={group.rows} />
                  </details>
                ))
              )}
            </section>
          )}
        </>
      )}
    </>
  );
}
