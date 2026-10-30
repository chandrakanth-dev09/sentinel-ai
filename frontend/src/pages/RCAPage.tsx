import { useState, type FormEvent } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusPill } from "../components/Feedback";
import { analyzeRootCause, getErrorMessage, getServices } from "../services/api";
import { useAsyncResource } from "../hooks/useAsyncResource";
import type { RCAResult } from "../types";

export function RCAPage() {
  const services = useAsyncResource("rca-service-filter", getServices);
  const [lookback, setLookback] = useState(60);
  const [serviceId, setServiceId] = useState("");
  const [result, setResult] = useState<RCAResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const analysis = await analyzeRootCause(lookback, serviceId || undefined);
      setResult(analysis);
    } catch (reason) {
      setError(getErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack">
      <PageHeader title="Root-cause analysis" subtitle="Rank likely upstream causes from observed telemetry, logs, anomalies, and service dependencies." />
      {services.error && <ErrorState message={services.error} onRetry={services.reload} />}
      <form className="panel rca-controls" onSubmit={(event) => void submit(event)}>
        <label>Lookback window <span className="field-control"><input type="number" min={1} max={1440} value={lookback} onChange={(event) => setLookback(Number(event.target.value))} required /><span>minutes</span></span></label>
        <label>Focus service <select value={serviceId} onChange={(event) => setServiceId(event.target.value)}><option value="">All services</option>{(services.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <button className="button button-primary" disabled={loading || services.loading}>{loading ? "Analyzing…" : "Analyze current signals"}</button>
      </form>
      {error && <p className="notice notice-error" role="alert">{error}</p>}
      {!result && !loading && <EmptyState title="No analysis run yet" children="Choose a lookback window and analyze available system signals." />}
      {loading && <LoadingState label="Correlating signals and dependency impact…" />}
      {result && <RCAResults result={result} />}
    </div>
  );
}

function RCAResults({ result }: { result: RCAResult }) {
  return <>
    <section className="panel rca-result">
      <div className="panel-heading"><h2>Probable root cause</h2><span className="panel-meta">Analysis window: {new Date(result.analysis_start).toLocaleString()} — {new Date(result.analysis_end).toLocaleString()}</span></div>
      {result.probable_root_cause ? <div className="root-cause-card"><span className="root-cause-icon">!</span><div><strong>{result.probable_root_cause.service_name}</strong><p>Ranking score {result.probable_root_cause.ranking_score.toFixed(3)} · {result.probable_root_cause.downstream_affected_count} downstream service(s) · {result.probable_root_cause.supporting_evidence_count} evidence items</p></div><StatusPill value="PROBABLE" /></div> : <EmptyState title="No probable root cause met the evidence criteria" children="Review the timeline and supporting evidence before drawing conclusions." />}
      <p className="method-note">The ranking score is a heuristic, not a calibrated probability. Method: {result.ranking_method}</p>
    </section>
    <div className="two-column-grid">
      <section className="panel"><div className="panel-heading"><h2>Incident timeline</h2><span className="panel-meta">{result.incident_timeline.length} events</span></div>
        {result.incident_timeline.length ? <div className="evidence-list">{result.incident_timeline.map((item, index) => <article className="evidence-item" key={`${item.timestamp}-${item.service_id}-${index}`}><span className="timeline-dot" /><div className="evidence-content"><div className="evidence-heading"><strong>{item.service_name} · {item.evidence_type.replaceAll("_", " ")}</strong><time>{new Date(item.timestamp).toLocaleString()}</time></div><p>{item.summary}</p></div></article>)}</div> : <EmptyState title="No events matched the selected window" />}</section>
      <section className="panel"><div className="panel-heading"><h2>Alternative candidates</h2></div>
        {result.alternative_causes.length ? <div className="candidate-list">{result.alternative_causes.map((item) => <div className="candidate-row" key={item.service_id}><strong>{item.service_name}</strong><span>Score {item.ranking_score.toFixed(3)}</span><small>{item.supporting_evidence_count} evidence · {item.downstream_affected_count} downstream</small></div>)}</div> : <EmptyState title="No alternative causes ranked" />}
      </section>
    </div>
    <div className="two-column-grid">
      <section className="panel"><div className="panel-heading"><h2>Supporting evidence</h2><span className="panel-meta">{result.supporting_evidence.length} items</span></div>
        {result.supporting_evidence.length ? <div className="evidence-list">{result.supporting_evidence.map((item, index) => <article className="evidence-item evidence-compact" key={`${item.timestamp}-${item.service_id}-${index}`}><span className="timeline-dot" /><div className="evidence-content"><div className="evidence-heading"><strong>{item.service_name} · {item.evidence_type.replaceAll("_", " ")}</strong><StatusPill value={item.strength >= 0.75 ? "HIGH" : item.strength >= 0.45 ? "MEDIUM" : "LOW"} /></div><p>{item.summary}</p><small>{new Date(item.timestamp).toLocaleString()}</small></div></article>)}</div> : <EmptyState title="No supporting evidence returned" />}
      </section>
      <section className="panel"><div className="panel-heading"><h2>Recommended investigation steps</h2></div>
        {result.recommended_investigation_steps.length ? <ol className="recommendation-list">{result.recommended_investigation_steps.map((step, index) => <li key={`${index}-${step}`}>{step}</li>)}</ol> : <EmptyState title="No next steps recommended" />}
      </section>
    </div>
  </>;
}
