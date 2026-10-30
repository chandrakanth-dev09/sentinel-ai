import { useEffect, useState, type FormEvent } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "../components/Feedback";
import { getConfiguration, getErrorMessage, getServices, registerDependency, registerService, updateConfiguration } from "../services/api";
import { useAsyncResource } from "../hooks/useAsyncResource";
import type { AppConfiguration } from "../types";

type ConfigurationKey = keyof Omit<AppConfiguration, "updated_at">;

const configurationFields: Array<{ key: ConfigurationKey; label: string; min: number; max?: number; step: number; suffix: string }> = [
  { key: "monitoring_interval_seconds", label: "Monitoring interval", min: 1, max: 3600, step: 1, suffix: "seconds" },
  { key: "cpu_warning_percent", label: "CPU warning threshold", min: 0, max: 100, step: 0.1, suffix: "%" },
  { key: "memory_warning_percent", label: "Memory warning threshold", min: 0, max: 100, step: 0.1, suffix: "%" },
  { key: "disk_warning_percent", label: "Disk warning threshold", min: 0, max: 100, step: 0.1, suffix: "%" },
  { key: "response_time_warning_ms", label: "Response time warning", min: 0.01, step: 1, suffix: "ms" },
  { key: "error_rate_warning_percent", label: "Error rate warning threshold", min: 0, max: 100, step: 0.1, suffix: "%" },
  { key: "availability_warning_percent", label: "Availability warning threshold", min: 0, max: 100, step: 0.1, suffix: "%" }
];

export function SettingsPage() {
  const configuration = useAsyncResource("configuration", getConfiguration);
  const services = useAsyncResource("settings-services", getServices);
  const [draft, setDraft] = useState<AppConfiguration | null>(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: "success" | "error"; message: string } | null>(null);
  const [serviceName, setServiceName] = useState("");
  const [serviceDescription, setServiceDescription] = useState("");
  const [simulated, setSimulated] = useState(false);
  const [upstreamId, setUpstreamId] = useState("");
  const [downstreamId, setDownstreamId] = useState("");
  const [registering, setRegistering] = useState(false);

  useEffect(() => {
    if (configuration.data) setDraft(configuration.data);
  }, [configuration.data]);

  const saveConfiguration = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft) return;
    setSaving(true);
    setFeedback(null);
    try {
      const { updated_at: _updatedAt, ...updates } = draft;
      await updateConfiguration(updates);
      setFeedback({ kind: "success", message: "Monitoring thresholds saved." });
      configuration.reload();
    } catch (error) {
      setFeedback({ kind: "error", message: getErrorMessage(error) });
    } finally {
      setSaving(false);
    }
  };

  const addService = async (event: FormEvent) => {
    event.preventDefault();
    setRegistering(true);
    setFeedback(null);
    try {
      await registerService({ name: serviceName.trim(), description: serviceDescription.trim() || undefined, is_simulated: simulated });
      setServiceName("");
      setServiceDescription("");
      setFeedback({ kind: "success", message: "Service registered." });
      services.reload();
    } catch (error) {
      setFeedback({ kind: "error", message: getErrorMessage(error) });
    } finally {
      setRegistering(false);
    }
  };

  const addDependency = async (event: FormEvent) => {
    event.preventDefault();
    setRegistering(true);
    setFeedback(null);
    try {
      await registerDependency({ upstream_service_id: upstreamId, downstream_service_id: downstreamId });
      setUpstreamId("");
      setDownstreamId("");
      setFeedback({ kind: "success", message: "Dependency registered." });
    } catch (error) {
      setFeedback({ kind: "error", message: getErrorMessage(error) });
    } finally {
      setRegistering(false);
    }
  };

  if (configuration.loading || services.loading) return <LoadingState label="Loading monitoring settings…" />;
  if (configuration.error) return <ErrorState message={configuration.error} onRetry={configuration.reload} />;
  if (!draft) return <EmptyState title="Settings are unavailable" />;
  const currentServices = services.data ?? [];
  const canRegisterDependency = currentServices.length > 1 && upstreamId && downstreamId && upstreamId !== downstreamId;

  return (
    <div className="page-stack">
      <PageHeader title="Monitoring settings" subtitle="Configure service health thresholds, register services, and define dependency relationships." />
      {feedback && <p className={`notice notice-${feedback.kind}`} role={feedback.kind === "error" ? "alert" : "status"}>{feedback.message}</p>}
      <form className="panel settings-form" onSubmit={(event) => void saveConfiguration(event)}>
        <div className="panel-heading"><div><h2>Health thresholds</h2><p className="panel-description">Updates are persisted by the API and used when classifying ingested service metrics.</p></div><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : "Save thresholds"}</button></div>
        <div className="settings-grid">{configurationFields.map((field) => <label key={field.key}>{field.label}<span className="field-control"><input type="number" min={field.min} max={field.max} step={field.step} value={draft[field.key]} onChange={(event) => setDraft((current) => current ? { ...current, [field.key]: Number(event.target.value) } : current)} required /><span>{field.suffix}</span></span></label>)}</div>
        <p className="last-updated">Last updated: {new Date(draft.updated_at).toLocaleString()}</p>
      </form>
      {services.error ? <ErrorState message={services.error} onRetry={services.reload} /> : <>
        <form className="panel settings-form" onSubmit={(event) => void addService(event)}>
          <div className="panel-heading"><div><h2>Register service</h2><p className="panel-description">New services start with unknown health until telemetry arrives.</p></div></div>
          <div className="settings-grid service-registration">
            <label>Service name<input value={serviceName} maxLength={120} onChange={(event) => setServiceName(event.target.value)} required /></label>
            <label>Description<input value={serviceDescription} maxLength={500} onChange={(event) => setServiceDescription(event.target.value)} /></label>
            <label className="checkbox-field"><input type="checkbox" checked={simulated} onChange={(event) => setSimulated(event.target.checked)} /> Mark as simulated data</label>
          </div>
          <button className="button button-secondary" disabled={registering}>{registering ? "Registering…" : "Register service"}</button>
        </form>
        <form className="panel settings-form" onSubmit={(event) => void addDependency(event)}>
          <div className="panel-heading"><div><h2>Define dependency</h2><p className="panel-description">Specify which upstream service another service depends on.</p></div></div>
          {currentServices.length < 2 ? <EmptyState title="Register at least two services to define a dependency" /> : <div className="settings-grid service-registration">
            <label>Upstream service<select value={upstreamId} onChange={(event) => setUpstreamId(event.target.value)} required><option value="">Select service…</option>{currentServices.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}</select></label>
            <label>Downstream service<select value={downstreamId} onChange={(event) => setDownstreamId(event.target.value)} required><option value="">Select service…</option>{currentServices.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}</select></label>
          </div>}
          {currentServices.length > 1 && <button className="button button-secondary" disabled={registering || !canRegisterDependency}>{registering ? "Saving…" : "Add dependency"}</button>}
        </form>
        <section className="panel table-panel"><div className="panel-heading"><h2>Registered services</h2><span className="panel-meta">{currentServices.length} services</span></div>
          {!currentServices.length ? <EmptyState title="No services are registered" /> : <div className="table-scroll"><table><thead><tr><th>Service</th><th>Health</th><th>Type</th><th>Service ID</th></tr></thead><tbody>{currentServices.map((service) => <tr key={service.id}><td>{service.name}</td><td>{service.health_status}</td><td>{service.is_simulated ? "Simulated" : "Monitored"}</td><td><code>{service.id}</code></td></tr>)}</tbody></table></div>}
        </section>
      </>}
    </div>
  );
}
