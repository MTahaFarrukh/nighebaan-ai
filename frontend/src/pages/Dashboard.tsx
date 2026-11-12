import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { getAlerts } from "../api";
import { Empty, ErrorNotice, Loading, PageHeader } from "../components/ui";
export default function Dashboard() {
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: ["alerts", offset],
    queryFn: ({ signal }) => getAlerts(offset, signal),
  });
  const data = query.data;
  const days = Object.entries(data?.by_day ?? {}).map(([day, count]) => ({
    day,
    count,
  }));
  return (
    <>
      <PageHeader
        eyebrow="LOCAL ACTIVITY"
        title="Your risk overview."
        description="High-risk web analyses only. These records are not sent notifications."
        action={
          <button
            className="secondary"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            Refresh
          </button>
        }
      />
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorNotice
          message="History could not be loaded."
          retry={() => void query.refetch()}
        />
      ) : (
        data && (
          <>
            <div className="stat-grid">
              <div className="panel stat">
                <span>High-risk results</span>
                <strong>{data.total}</strong>
                <small>Across local history</small>
              </div>
              <div className="panel stat">
                <span>Message analyses</span>
                <strong>{data.by_modality.text ?? 0}</strong>
                <small>High risk only</small>
              </div>
              <div className="panel stat">
                <span>URL analyses</span>
                <strong>{data.by_modality.url ?? 0}</strong>
                <small>High risk only</small>
              </div>
              <div className="panel stat">
                <span>Media analyses</span>
                <strong>
                  {["image", "pdf", "audio", "video"].reduce(
                    (sum, kind) => sum + (data.by_modality[kind] ?? 0),
                    0,
                  )}
                </strong>
                <small>High risk only</small>
              </div>
            </div>
            {!data.total ? (
              <section className="panel mt">
                <Empty title="No high-risk results yet.">
                  Analyze a message or URL to get started. Only results marked
                  high risk appear here; content is never saved.
                </Empty>
              </section>
            ) : (
              <>
                <section className="panel mt">
                  <h2>Activity over time</h2>
                  <p className="muted small">
                    Daily high-risk result count · UTC dates
                  </p>
                  <div className="chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={days}>
                        <CartesianGrid stroke="#263944" vertical={false} />
                        <XAxis
                          dataKey="day"
                          tick={{ fill: "#91a6b2", fontSize: 11 }}
                        />
                        <YAxis
                          allowDecimals={false}
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
                          dataKey="count"
                          name="High-risk results"
                          fill="#4dd9ba"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </section>
                <section className="panel mt">
                  <div className="row between">
                    <h2>Recent high-risk results</h2>
                    <span className="badge neutral">Metadata only</span>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Time</th>
                          <th>Input</th>
                          <th>Prediction</th>
                          <th>Risk</th>
                          <th>Rules</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.items.map((row) => (
                          <tr key={row.id}>
                            <td>{new Date(row.ts).toLocaleString()}</td>
                            <td className="capitalize">{row.modality}</td>
                            <td className="capitalize">{row.label}</td>
                            <td>
                              <span className="badge high">
                                High · {row.risk_score.toFixed(2)}
                              </span>
                            </td>
                            <td>{row.rule_ids.join(", ") || "None"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="row between pagination">
                    <button
                      className="secondary"
                      disabled={!offset || query.isFetching}
                      onClick={() => setOffset(Math.max(0, offset - 20))}
                    >
                      Previous
                    </button>
                    <span className="small muted">
                      {offset + 1}–{Math.min(offset + 20, data.total)} of{" "}
                      {data.total}
                    </span>
                    <button
                      className="secondary"
                      disabled={offset + 20 >= data.total || query.isFetching}
                      onClick={() => setOffset(offset + 20)}
                    >
                      Next
                    </button>
                  </div>
                </section>
              </>
            )}
            <p className="privacy-note">
              Low and medium results are not retained. Counts do not represent
              all analyses or model accuracy.
            </p>
          </>
        )
      )}
    </>
  );
}
