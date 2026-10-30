import { Link, useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { EmptyState, ErrorState, LoadingState, PageHeader, SourcePill, StatusPill } from "../components/Feedback";
import { getService, getServiceMetrics, getServices } from "../services/api";
import { useAsyncResource } from "../hooks/useAsyncResource";

export function ServicesPage() {
  const resource = useAsyncResource("services-monitoring", getServices, 10000);
  if (resource.loading) return <LoadingState label="Loading monitored services…" />;
  if (resource.error) return <ErrorState message={resource.error} onRetry={resource.reload} />;

  const services = resource.data ?? [];
  return (
    <div className="page-stack">
      <PageHeader title="Service monitoring" subtitle="Current health and latest telemetry for every registered service." />
      {services.length === 0 ? <EmptyState title="No services are registered" children="Start the simulator or register a service in Settings." /> : (
        <section className="panel table-panel">
          <div className="panel-heading"><h2>Monitored services</h2><span className="panel-meta">{services.length} total</span></div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>Service</th><th>Health</th><th>CPU</th><th>Memory</th><th>Response</th><th>Error rate</th><th>Source</th><th>Last updated</th></tr></thead>
              <tbody>
                {services.map((service) => (
                  <tr key={service.id}>
                    <td><Link className="service-link" to={`/services/${service.id}`}>{service.name}</Link><small className="table-subtext">{service.description ?? "—"}</small></td>
                    <td><StatusPill value={service.health_status} /></td>
                    <td>{service.latest_metrics ? `${service.latest_metrics.cpu_utilization.toFixed(1)}%` : "—"}</td>
                    <td>{service.latest_metrics ? `${service.latest_metrics.memory_utilization.toFixed(1)}%` : "—"}</td>
                    <td>{service.latest_metrics ? `${service.latest_metrics.response_time_ms.toFixed(0)} ms` : "—"}</td>
                    <td>{service.latest_metrics ? `${service.latest_metrics.error_rate.toFixed(2)}%` : "—"}</td>
                    <td>{service.latest_metrics ? <SourcePill source={service.latest_metrics.source} /> : service.is_simulated ? <SourcePill source="SIMULATED" /> : "—"}</td>
                    <td>{service.latest_metrics ? new Date(service.latest_metrics.timestamp).toLocaleString() : "No samples"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export function ServiceDetailPage() {
  const { serviceId = "" } = useParams();
  const service = useAsyncResource(`service:${serviceId}`, () => getService(serviceId));
  const metrics = useAsyncResource(`service-metrics:${serviceId}`, () => getServiceMetrics(serviceId));
  if (service.loading || metrics.loading) return <LoadingState label="Loading service detail…" />;
  if (service.error) return <ErrorState message={service.error} onRetry={service.reload} />;
  if (metrics.error) return <ErrorState message={metrics.error} onRetry={metrics.reload} />;
  if (!service.data) return <EmptyState title="Service not found" />;

  const samples = metrics.data ?? [];
  const chartData = samples.map((item) => ({
    ...item,
    time: new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }));
  const latest = service.data.latest_metrics;
  return (
    <div className="page-stack">
      <PageHeader title={service.data.name} subtitle={service.data.description ?? "Service telemetry and health detail."} action={<Link className="button button-secondary" to="/services">Back to services</Link>} />
      <div className="detail-banner">
        <StatusPill value={service.data.health_status} />
        {service.data.is_simulated && <SourcePill source="SIMULATED" />}
        <span className="muted">Registered {new Date(service.data.created_at).toLocaleString()}</span>
      </div>
      <div className="stat-grid stat-grid-four">
        <StatTile label="CPU" value={latest ? `${latest.cpu_utilization.toFixed(1)}%` : "—"} />
        <StatTile label="Memory" value={latest ? `${latest.memory_utilization.toFixed(1)}%` : "—"} />
        <StatTile label="Response time" value={latest ? `${latest.response_time_ms.toFixed(0)} ms` : "—"} />
        <StatTile label="Error rate" value={latest ? `${latest.error_rate.toFixed(2)}%` : "—"} />
      </div>
      <section className="panel chart-panel"><div className="panel-heading"><h2>Recent performance</h2><span className="panel-meta">{samples.length} stored samples</span></div>
        {chartData.length === 0 ? <EmptyState title="No metrics recorded for this service" /> : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#243246" strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fill: "#8290a4", fontSize: 11 }} />
              <YAxis tick={{ fill: "#8290a4", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#111a28", border: "1px solid #243246", borderRadius: 8 }} />
              <Line type="monotone" dataKey="response_time_ms" name="Response ms" stroke="#f0b970" dot={false} />
              <Line type="monotone" dataKey="error_rate" name="Error %" stroke="#f17883" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return <article className="stat-card"><span className="stat-label">{label}</span><strong className="stat-value">{value}</strong></article>;
}
