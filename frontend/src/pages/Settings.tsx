import { useMutation, useQuery } from "@tanstack/react-query";
import { getSettings, simulateWhatsApp } from "../api";
import { ErrorNotice, Loading, PageHeader } from "../components/ui";
export default function Settings() {
  const simulation = useMutation({ mutationFn: simulateWhatsApp });
  const query = useQuery({
    queryKey: ["settings"],
    queryFn: ({ signal }) => getSettings(signal),
  });
  return (
    <>
      <PageHeader
        eyebrow="PREFERENCES & SAFEGUARDS"
        title="Know how protection works."
        description="Current backend policy and connection availability."
      />
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorNotice
          message="Settings could not be loaded."
          retry={() => void query.refetch()}
        />
      ) : (
        <div className="two-columns">
          <section className="panel">
            <h2>Risk thresholds</h2>
            <p className="muted">Read-only values from the running backend.</p>
            <dl className="settings-list">
              <div>
                <dt>Medium risk starts at</dt>
                <dd>{query.data.medium_threshold.toFixed(2)}</dd>
              </div>
              <div>
                <dt>High risk starts at</dt>
                <dd>{query.data.high_threshold.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Credential + link risk floor</dt>
                <dd>{query.data.credential_url_floor.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Dry-run configuration</dt>
                <dd>{query.data.dry_run ? "Enabled" : "Disabled"}</dd>
              </div>
            </dl>
            <p className="small muted">
              Thresholds have not been calibrated for guardian alerts.
            </p>
          </section>
          <section className="panel">
            <h2>WhatsApp &amp; guardian</h2>
            <p className="muted">Pair a dedicated account and manage consent in the local bridge. The simulator uses a built-in example and sends zero messages.</p>
            <button type="button" className="secondary" disabled={simulation.isPending} onClick={() => simulation.mutate()}>
              {simulation.isPending ? "Running…" : "Simulate WhatsApp alert"}
            </button>
            <div role="status">
              {simulation.data?.alert_guardian_text && <p>{simulation.data.alert_guardian_text}</p>}
              {simulation.data && !simulation.data.should_alert && <p>No alert triggered.</p>}
              {simulation.isError && <p>Simulation failed. Check the backend and text model.</p>}
            </div>
          </section>
        </div>
      )}
      <section className="panel mt">
        <h2>Privacy by default</h2>
        <p className="muted">
          Submitted content is processed in memory. Local history contains only
          time, modality, predicted label, risk and rule IDs. Your browser does
          not save analysis input in local storage.
        </p>
      </section>
    </>
  );
}
