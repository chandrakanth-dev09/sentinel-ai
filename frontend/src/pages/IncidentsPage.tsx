import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusPill } from "../components/Feedback";
import { analyzeIncident, getErrorMessage, getIncident, getIncidents, updateIncident } from "../services/api";
import { useAsyncResource } from "../hooks/useAsyncResource";
import type { IncidentStatus } from "../types";

export function IncidentsPage() {
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const resource = useAsyncResource(
    `incidents:${status}:${severity}`,
    () => getIncidents({ status: status || undefined, severity: severity || undefined })
  );
  if (resource.loading) return <LoadingState label="Loading incidents…" />;
  if (resource.error) return <ErrorState message={resource.error} onRetry={resource.reload} />;
  const incidents = resource.data ?? [];

  return (
    <div className="page-stack">
      <PageHeader title="Incident management" subtitle="Review, prioritize, and investigate active and historical incidents." />
      <section className="panel table-panel">
        <div className="panel-heading"><h2>Incidents</h2><div className="filter-row">
          <label className="sr-only" htmlFor="incident-status-filter">Filter by status</label>
          <select id="incident-status-filter" value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option>OPEN</option><option>INVESTIGATING</option><option>RESOLVED</option><option>CLOSED</option></select>
          <label className="sr-only" htmlFor="incident-severity-filter">Filter by severity</label>
          <select id="incident-severity-filter" value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="">All severities</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select>
        </div></div>
        {incidents.length === 0 ? <EmptyState title="No incidents match these filters" /> : <div className="table-scroll"><table>
          <thead><tr><th>Incident</th><th>Severity</th><th>Status</th><th>Root cause</th><th>Affected services</th><th>First detected</th></tr></thead>
          <tbody>{incidents.map((incident) => <tr key={incident.id}>
            <td><Link className="service-link" to={`/incidents/${incident.id}`}>{incident.title}</Link><small className="table-subtext">{incident.description}</small></td>
            <td><StatusPill value={incident.severity} /></td>
            <td><StatusPill value={incident.status} /></td>
            <td>{incident.root_cause_service_name ?? "Undetermined"}</td>
            <td>{incident.affected_services.join(", ") || "—"}</td>
            <td>{new Date(incident.first_detected_at).toLocaleString()}</td>
          </tr>)}</tbody>
        </table></div>}
      </section>
    </div>
  );
}

export function IncidentDetailPage() {
  const { incidentId = "" } = useParams();
  const incident = useAsyncResource(`incident:${incidentId}`, () => getIncident(incidentId));
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  if (incident.loading) return <LoadingState label="Loading incident detail…" />;
  if (incident.error) return <ErrorState message={incident.error} onRetry={incident.reload} />;
  if (!incident.data) return <EmptyState title="Incident not found" />;
  const record = incident.data;

  const transitionOptions: Record<IncidentStatus, IncidentStatus[]> = {
    OPEN: ["INVESTIGATING", "RESOLVED", "CLOSED"],
    INVESTIGATING: ["OPEN", "RESOLVED", "CLOSED"],
    RESOLVED: ["INVESTIGATING", "CLOSED"],
    CLOSED: []
  };
  const transition = async (nextStatus: IncidentStatus) => {
    setBusy(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      await updateIncident(record.id, { status: nextStatus });
      setActionSuccess(`Incident status updated to ${nextStatus}.`);
      incident.reload();
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };
  const runAnalysis = async () => {
    setBusy(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      await analyzeIncident(record.id);
      setActionSuccess("Root-cause analysis completed and incident evidence was updated.");
      incident.reload();
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page-stack">
      <PageHeader title={record.title} subtitle={record.description} action={<Link className="button button-secondary" to="/incidents">Back to incidents</Link>} />
      <section className="panel incident-summary">
        <div className="incident-summary-top"><div className="pill-row"><StatusPill value={record.severity} /><StatusPill value={record.status} /></div>
          <div className="filter-row">
            {transitionOptions[record.status].length > 0 && <select aria-label="Update incident status" disabled={busy} value="" onChange={(event) => { if (event.target.value) void transition(event.target.value as IncidentStatus); }}><option value="">Change status…</option>{transitionOptions[record.status].map((value) => <option key={value}>{value}</option>)}</select>}
            <button className="button button-primary" disabled={busy} onClick={() => void runAnalysis()}>{busy ? "Working…" : "Reanalyze incident"}</button>
          </div>
        </div>
        {actionError && <p className="notice notice-error" role="alert">{actionError}</p>}
        {actionSuccess && <p className="notice notice-success" role="status">{actionSuccess}</p>}
        <div className="incident-facts"><div><span>First detected</span><strong>{new Date(record.first_detected_at).toLocaleString()}</strong></div><div><span>Last updated</span><strong>{new Date(record.last_updated_at).toLocaleString()}</strong></div><div><span>Probable root cause</span><strong>{record.root_cause_service_name ?? "Undetermined"}</strong></div><div><span>Affected services</span><strong>{record.affected_services.join(", ") || "—"}</strong></div></div>
        {record.explanation && <div className="analysis-box"><h2>Analysis summary</h2><p>{record.explanation}</p></div>}
        {record.recommended_actions?.length ? <div className="analysis-box"><h2>Recommended actions</h2><ul>{record.recommended_actions.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
      </section>
      <section className="panel table-panel"><div className="panel-heading"><h2>Evidence timeline</h2><span className="panel-meta">{record.evidence?.length ?? 0} records</span></div>
        {record.evidence?.length ? <div className="evidence-list">{record.evidence.map((item) => <article className="evidence-item" key={item.id}>
          <span className="timeline-dot" /><div className="evidence-content"><div className="evidence-heading"><strong>{item.evidence_type.replaceAll("_", " ")}</strong><time>{new Date(item.event_timestamp).toLocaleString()}</time></div><p>{item.summary}</p>{item.details && <details><summary>Evidence details</summary><pre>{JSON.stringify(item.details, null, 2)}</pre></details>}</div>
        </article>)}</div> : <EmptyState title="No evidence has been attached" children="Run an analysis to collect matching metrics, logs, and anomaly events." />}
      </section>
    </div>
  );
}
