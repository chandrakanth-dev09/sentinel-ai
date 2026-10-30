import { EmptyState, ErrorState, LoadingState, PageHeader, SourcePill, StatusPill } from "../components/Feedback";
import { getAnomalyHistory, getModelStatus } from "../services/api";
import { useAsyncResource } from "../hooks/useAsyncResource";

export function ModelPage() {
  const model = useAsyncResource("model-status", getModelStatus, 30000);
  const history = useAsyncResource("model-anomaly-history", getAnomalyHistory, 30000);
  if (model.loading || history.loading) return <LoadingState label="Loading model status and anomaly history…" />;
  if (model.error) return <ErrorState message={model.error} onRetry={model.reload} />;
  if (history.error) return <ErrorState message={history.error} onRetry={history.reload} />;
  if (!model.data) return <EmptyState title="Model status is unavailable" />;

  const metrics = model.data.evaluation_metrics ?? {};
  return (
    <div className="page-stack">
      <PageHeader title="Anomaly detection model" subtitle="Model readiness, evaluation context, and persisted detection events." action={<StatusPill value={model.data.is_trained ? "TRAINED" : "NOT TRAINED"} />} />
      <section className="panel model-overview">
        <div className="panel-heading"><h2>Model information</h2>{model.data.version && <span className="panel-meta">Version {model.data.version}</span>}</div>
        {model.data.is_trained ? <div className="incident-facts">
          <div><span>Model</span><strong>{model.data.model_name ?? "—"}</strong></div>
          <div><span>Trained at</span><strong>{model.data.trained_at ? new Date(model.data.trained_at).toLocaleString() : "—"}</strong></div>
          <div><span>Evaluation dataset</span><strong>{model.data.dataset_name ?? "—"}</strong></div>
          <div><span>Dataset source</span><strong>{model.data.dataset_source ?? "—"}</strong></div>
        </div> : <div className="notice notice-warning">{model.data.detail ?? "Train a model to enable anomaly detection."}</div>}
      </section>
      <section className="panel"><div className="panel-heading"><h2>Evaluation metrics</h2><span className="panel-meta">Dataset measurements, not production guarantees</span></div>
        {Object.keys(metrics).length === 0 ? <EmptyState title="No evaluation metrics are available" /> : <div className="metric-grid">{Object.entries(metrics).map(([name, value]) => <div className="metric-card" key={name}><span>{name.replaceAll("_", " ")}</span><strong>{typeof value === "number" ? value.toFixed(4) : value}</strong></div>)}</div>}
      </section>
      <section className="panel table-panel"><div className="panel-heading"><h2>Recent detection events</h2><span className="panel-meta">{history.data?.total ?? 0} total events</span></div>
        {!history.data?.items.length ? <EmptyState title="No anomaly events have been persisted" /> : <div className="table-scroll"><table>
          <thead><tr><th>Detected</th><th>Service</th><th>Result</th><th>Severity</th><th>Score</th><th>Model version</th></tr></thead>
          <tbody>{history.data.items.map((item) => <tr key={item.anomaly_event_id}>
            <td>{new Date(item.detected_at).toLocaleString()}</td><td>{item.service_name}</td><td>{item.is_anomaly ? "Anomaly" : "Normal"}</td><td><StatusPill value={item.severity} /></td><td>{item.anomaly_score.toFixed(4)}</td><td><SourcePill source={item.model_version} /></td>
          </tr>)}</tbody>
        </table></div>}
      </section>
    </div>
  );
}
