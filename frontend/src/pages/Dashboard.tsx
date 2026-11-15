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

function alertStateLabel(state: string | null | undefined) {
  switch (state) {
    case "dry_run":
      return "Dry run · not sent";
    case "reserved":
      return "Eligible · delivery unconfirmed";
    case "duplicate":
      return "Duplicate";
    case "rate_limited":
      return "Rate limited";
    case "below_threshold":
      return "Not eligible";
    default:
      return "No alert";
  }
}

export default function Dashboard() {
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: ["alerts", offset],
    queryFn: ({ signal }) => getAlerts(offset, signal),
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
  });
  const data = query.data;
  const days = Object.entries(data?.by_day ?? {}).map(([day, count]) => ({
    day,
    count,
  }));
  const whatsappCount =
    data?.items.filter((row) => row.source === "whatsapp").length ?? 0;
  const webCount = (data?.items.length ?? 0) - whatsappCount;
  const dryRunCount =
    data?.items.filter(
      (row) => row.source === "whatsapp" && row.alert_state === "dry_run",
    ).length ?? 0;
  return (
    <>
      <PageHeader
        eyebrow="LOCAL ACTIVITY"
        title="A clearer view of risk."
        description="High-risk results from the web app and consenting WhatsApp demo account. Privacy-safe metadata refreshes every 10 seconds."
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
                <span>WhatsApp results</span>
                <strong>{whatsappCount}</strong>
                <small>On this page · all modalities</small>
              </div>
              <div className="panel stat">
                <span>Web app results</span>
                <strong>{webCount}</strong>
                <small>On this page · all modalities</small>
              </div>
              <div className="panel stat">
                <span>Dry-run alerts</span>
                <strong>{dryRunCount}</strong>
                <small>Not delivered · on this page</small>
              </div>
            </div>
            {!data.total ? (
              <section className="panel mt">
                <Empty title="No high-risk results yet.">
                  Analyze a message or URL, or connect the consenting WhatsApp
                  demo account. Only high-risk metadata appears here; message
                  content is never saved.
                </Empty>
              </section>
            ) : (
              <>
                <section className="panel mt">
                  <h2>Activity over time</h2>
                  <p className="muted small">
                    Daily high-risk result count from web and WhatsApp · UTC
                    dates
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
                          <th>Source</th>
                          <th>Type</th>
                          <th>Prediction</th>
                          <th>Risk</th>
                          <th>Rules</th>
                          <th>Alert status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.items.map((row) => (
                          <tr key={row.id}>
                            <td>{new Date(row.ts).toLocaleString()}</td>
                            <td>
                              <span
                                className={`badge ${row.source === "whatsapp" ? "whatsapp" : "neutral"}`}
                              >
                                {row.source === "whatsapp" ? "WhatsApp" : "Web app"}
                              </span>
                            </td>
                            <td className="capitalize">{row.modality}</td>
                            <td className="capitalize">{row.label}</td>
                            <td>
                              <span className="badge high">
                                High · {row.risk_score.toFixed(2)}
                              </span>
                            </td>
                            <td>{row.rule_ids.join(", ") || "None"}</td>
                            <td>
                              <span
                                className={`badge ${row.alert_state === "dry_run" ? "medium" : row.source === "whatsapp" ? "neutral" : "low"}`}
                              >
                                {row.source === "whatsapp"
                                  ? alertStateLabel(row.alert_state)
                                  : "Web result"}
                              </span>
                            </td>
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
              Source and dry-run counts cover the current page; the chart and
              total cover all saved high-risk results. Low and medium results
              are not retained, and alert eligibility does not confirm delivery.
            </p>
          </>
        )
      )}
    </>
  );
}
