import { useState, type FormEvent } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeader, SourcePill, StatusPill } from "../components/Feedback";
import { getLogs, getServices } from "../services/api";
import { useAsyncResource } from "../hooks/useAsyncResource";

export function LogsPage() {
  const services = useAsyncResource("log-service-filter", getServices);
  const [serviceId, setServiceId] = useState("");
  const [level, setLevel] = useState("");
  const [search, setSearch] = useState("");
  const [submitted, setSubmitted] = useState({ serviceId: "", level: "", search: "" });
  const logs = useAsyncResource(
    `logs:${submitted.serviceId}:${submitted.level}:${submitted.search}`,
    () => getLogs({
      service_id: submitted.serviceId || undefined,
      level: submitted.level || undefined,
      search: submitted.search.trim() || undefined
    })
  );
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted({ serviceId, level, search });
  };

  return (
    <div className="page-stack">
      <PageHeader title="Log explorer" subtitle="Search application logs by service, severity, and message content." />
      {services.error && <ErrorState message={services.error} onRetry={services.reload} />}
      <form className="panel log-filters" onSubmit={submit}>
        <label>Service<select value={serviceId} onChange={(event) => setServiceId(event.target.value)}><option value="">All services</option>{(services.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Severity<select value={level} onChange={(event) => setLevel(event.target.value)}><option value="">All levels</option><option>INFO</option><option>WARNING</option><option>ERROR</option><option>CRITICAL</option></select></label>
        <label className="log-search">Message contains<input value={search} maxLength={200} onChange={(event) => setSearch(event.target.value)} placeholder="Search log messages" /></label>
        <button className="button button-primary" type="submit">Search logs</button>
      </form>
      {logs.loading ? <LoadingState label="Searching logs…" /> : logs.error ? <ErrorState message={logs.error} onRetry={logs.reload} /> : (
        <section className="panel table-panel">
          <div className="panel-heading"><h2>Application logs</h2><span className="panel-meta">{logs.data?.length ?? 0} most recent results</span></div>
          {!logs.data?.length ? <EmptyState title="No logs match this search" /> : <div className="log-list">{logs.data.map((log) => <article className="log-row" key={log.id}>
            <time>{new Date(log.timestamp).toLocaleString()}</time><StatusPill value={log.level} /><span className="log-service">{services.data?.find((item) => item.id === log.service_id)?.name ?? log.service_id}</span><p>{log.message}</p><SourcePill source={log.source} />
            {(log.error_type || log.trace_id || log.request_id) && <small className="log-metadata">{[log.error_type && `Error: ${log.error_type}`, log.trace_id && `Trace: ${log.trace_id}`, log.request_id && `Request: ${log.request_id}`].filter(Boolean).join(" · ")}</small>}
          </article>)}</div>}
        </section>
      )}
    </div>
  );
}
