import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatCard, StatusPill } from "../components/Feedback";
import { getAnomalyHistory, getMetrics, getOverview, isApiConfigured } from "../services/api";
import { useAsyncResource } from "../hooks/useAsyncResource";

const chartColors = ["#4ed6b6", "#7d9cff", "#f0b970"];

function ChartPanel({ title, children }: { title: string; children: ReactNode }) {
  return <section className="panel chart-panel"><div className="panel-heading"><h2>{title}</h2><span className="panel-meta">Recent samples</span></div>{children}</section>;
}

function StaticDashboard() {
  return (
    <div className="page-stack">
      <PageHeader
        title="System overview"
        subtitle="SentinelAI service monitoring and incident management interface."
        action={<span className="source-pill">FRONTEND PREVIEW</span>}
      />
      <p className="notice notice-warning">
        This GitHub Pages deployment hosts the interface only. Connect a separately hosted SentinelAI API to load telemetry and enable dashboard actions.
      </p>
      <div className="stat-grid">
        <StatCard label="Monitored services" value="—" detail="Backend API required" />
        <StatCard label="Degraded / critical" value="—" detail="Backend API required" />
        <StatCard label="Active incidents" value="—" detail="Backend API required" />
        <StatCard label="Anomalies · 24h" value="—" detail="Backend API required" />
        <StatCard label="Availability" value="—" detail="Backend API required" />
      </div>
      <div className="chart-grid">
        <ChartPanel title="CPU and memory utilization"><EmptyState title="Connect the API to load telemetry" /></ChartPanel>
        <ChartPanel title="Response time and error rate"><EmptyState title="Connect the API to load telemetry" /></ChartPanel>
        <ChartPanel title="Anomaly frequency"><EmptyState title="Connect the API to load anomaly history" /></ChartPanel>
        <section className="panel recent-panel"><div className="panel-heading"><h2>Recent incidents</h2></div><EmptyState title="Connect the API to load incidents" /></section>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const overview = useAsyncResource("overview", isApiConfigured ? getOverview : async () => null, 15000);
  const metrics = useAsyncResource("all-metrics", isApiConfigured ? getMetrics : async () => null, 15000);
  const anomalies = useAsyncResource("anomaly-history", isApiConfigured ? getAnomalyHistory : async () => null, 30000);

  if (!isApiConfigured) return <StaticDashboard />;

  if (overview.loading || metrics.loading || anomalies.loading) return <LoadingState label="Loading monitoring overview…" />;
  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.reload} />;
  if (metrics.error) return <ErrorState message={metrics.error} onRetry={metrics.reload} />;
  if (anomalies.error) return <ErrorState message={anomalies.error} onRetry={anomalies.reload} />;
  if (!overview.data) return <EmptyState title="Overview data is not available" />;

  const chartData = (metrics.data ?? []).map((metric) => ({
    ...metric,
    time: new Date(metric.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }));
  const anomalyCounts = new Map<string, number>();
  for (const anomaly of anomalies.data?.items ?? []) {
    if (!anomaly.is_anomaly) continue;
    const bucket = new Date(anomaly.detected_at).toLocaleDateString();
    anomalyCounts.set(bucket, (anomalyCounts.get(bucket) ?? 0) + 1);
  }

  const anomalyChartData = [...anomalyCounts.entries()].map(([date, count]) => ({ date, count }));
  const dataSource = overview.data.total_services === 0
    ? "Register a service or start the simulator to populate live telemetry."
    : `${overview.data.total_services} monitored services`;

  return (
    <div className="page-stack">
      <PageHeader
        title="System overview"
        subtitle="Live health, telemetry, and incident activity across monitored services."
        action={<span className="source-pill">API · {dataSource}</span>}
      />
      <div className="stat-grid">
        <StatCard label="Monitored services" value={overview.data.total_services} detail={`${overview.data.healthy_services} healthy`} tone="good" />
        <StatCard label="Degraded / critical" value={overview.data.degraded_services + overview.data.critical_services} detail={`${overview.data.critical_services} critical`} tone={overview.data.critical_services ? "danger" : "warning"} />
        <StatCard label="Active incidents" value={overview.data.active_incidents} detail="Open or investigating" tone={overview.data.active_incidents ? "warning" : "good"} />
        <StatCard label="Anomalies · 24h" value={overview.data.anomalies_last_24_hours} detail="Persisted model events" />
        <StatCard label="Availability" value={overview.data.availability_percent === null ? "—" : `${overview.data.availability_percent.toFixed(2)}%`} detail="Mean of latest service samples" tone="good" />
      </div>

      <div className="chart-grid">
        <ChartPanel title="CPU and memory utilization">
          {chartData.length === 0 ? <EmptyState title="No metric samples yet" /> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData}>
                <CartesianGrid stroke="#243246" strokeDasharray="3 3" />
                <XAxis dataKey="time" tick={{ fill: "#8290a4", fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: "#8290a4", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#111a28", border: "1px solid #243246", borderRadius: 8 }} />
                <Legend />
                <Line type="monotone" dataKey="cpu_utilization" name="CPU %" stroke={chartColors[0]} dot={false} />
                <Line type="monotone" dataKey="memory_utilization" name="Memory %" stroke={chartColors[1]} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartPanel>
        <ChartPanel title="Response time and error rate">
          {chartData.length === 0 ? <EmptyState title="No metric samples yet" /> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData}>
                <CartesianGrid stroke="#243246" strokeDasharray="3 3" />
                <XAxis dataKey="time" tick={{ fill: "#8290a4", fontSize: 11 }} />
                <YAxis yAxisId="left" tick={{ fill: "#8290a4", fontSize: 11 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: "#8290a4", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#111a28", border: "1px solid #243246", borderRadius: 8 }} />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="response_time_ms" name="Response ms" stroke={chartColors[2]} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="error_rate" name="Error %" stroke="#f17883" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartPanel>
        <ChartPanel title="Anomaly frequency">
          {anomalyChartData.length === 0 ? <EmptyState title="No anomaly events in the retrieved history" /> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={anomalyChartData}>
                <CartesianGrid stroke="#243246" strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fill: "#8290a4", fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fill: "#8290a4", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#111a28", border: "1px solid #243246", borderRadius: 8 }} />
                <Line type="monotone" dataKey="count" name="Anomalies" stroke="#f17883" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartPanel>
        <section className="panel recent-panel">
          <div className="panel-heading"><h2>Recent incidents</h2><Link to="/incidents" className="text-link">View all</Link></div>
          {overview.data.recent_incidents.length === 0 ? <EmptyState title="No incidents recorded" /> : (
            <div className="incident-preview-list">
              {overview.data.recent_incidents.map((incident) => (
                <Link className="incident-preview" to={`/incidents/${incident.id}`} key={incident.id}>
                  <span className={`severity-mark severity-${incident.severity.toLowerCase()}`} />
                  <span className="incident-preview-copy"><strong>{incident.title}</strong><small>{incident.affected_services.join(", ") || "No affected service recorded"}</small></span>
                  <StatusPill value={incident.status} />
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
