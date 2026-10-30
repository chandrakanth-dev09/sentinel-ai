export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type IncidentStatus = "OPEN" | "INVESTIGATING" | "RESOLVED" | "CLOSED";

export interface Metric {
  id: string;
  service_id: string;
  timestamp: string;
  cpu_utilization: number;
  memory_utilization: number;
  disk_utilization: number;
  network_traffic: number;
  response_time_ms: number;
  request_count: number;
  error_rate: number;
  database_connections: number;
  service_availability: number;
  source: "SIMULATED" | "AGENT" | "IMPORTED";
}

export interface Service {
  id: string;
  name: string;
  description: string | null;
  health_status: "UNKNOWN" | "HEALTHY" | "DEGRADED" | "CRITICAL";
  is_simulated: boolean;
  created_at: string;
  updated_at: string;
  latest_metrics: Omit<Metric, "id" | "service_id" | "network_traffic" | "request_count"> & {
    database_connections: number;
    source: string;
  } | null;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  root_cause_service_id: string | null;
  root_cause_service_name: string | null;
  affected_services: string[];
  first_detected_at: string;
  last_updated_at: string;
  resolved_at: string | null;
  explanation: string | null;
  recommended_actions: string[] | null;
  evidence?: IncidentEvidence[];
}

export interface IncidentEvidence {
  id: string;
  evidence_type: string;
  summary: string;
  details: Record<string, unknown> | null;
  event_timestamp: string;
  service_id: string | null;
  metric_id: string | null;
  application_log_id: string | null;
  anomaly_event_id: string | null;
}

export interface Overview {
  total_services: number;
  healthy_services: number;
  degraded_services: number;
  critical_services: number;
  unknown_services: number;
  active_incidents: number;
  anomalies_last_24_hours: number;
  availability_percent: number | null;
  recent_incidents: Incident[];
}

export interface DependencyGraph {
  nodes: Array<{
    id: string;
    name: string;
    health_status: Service["health_status"];
    is_simulated: boolean;
    latest_metrics: Service["latest_metrics"];
    active_incident_ids: string[];
  }>;
  edges: Array<{ upstream_service_id: string; downstream_service_id: string }>;
}

export interface ApplicationLog {
  id: string;
  service_id: string;
  timestamp: string;
  level: "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  message: string;
  error_type: string | null;
  trace_id: string | null;
  request_id: string | null;
  source: "SIMULATED" | "AGENT" | "IMPORTED";
  attributes: Record<string, unknown> | null;
}

export interface RCAEvidence {
  service_id: string;
  service_name: string;
  evidence_type: string;
  timestamp: string;
  summary: string;
  strength: number;
  details: Record<string, unknown>;
  metric_id: string | null;
  application_log_id: string | null;
  anomaly_event_id: string | null;
}

export interface RCACandidate {
  service_id: string;
  service_name: string;
  ranking_score: number;
  downstream_affected_count: number;
  first_signal_at: string;
  supporting_evidence_count: number;
}

export interface RCAResult {
  analysis_start: string;
  analysis_end: string;
  probable_root_cause: RCACandidate | null;
  affected_services: string[];
  incident_timeline: Array<{
    timestamp: string;
    service_id: string;
    service_name: string;
    evidence_type: string;
    summary: string;
  }>;
  supporting_evidence: RCAEvidence[];
  alternative_causes: RCACandidate[];
  recommended_investigation_steps: string[];
  ranking_method: string;
}

export interface ModelStatus {
  is_trained: boolean;
  model_name: string | null;
  version: string | null;
  trained_at: string | null;
  dataset_name: string | null;
  dataset_source: string | null;
  evaluation_metrics: Record<string, number> | null;
  detail: string | null;
}

export interface AnomalyHistory {
  total: number;
  items: Array<{
    anomaly_event_id: string;
    service_id: string;
    service_name: string;
    metric_id: string | null;
    is_anomaly: boolean;
    anomaly_score: number;
    severity: Severity;
    model_version: string;
    detected_at: string;
  }>;
}

export interface AppConfiguration {
  monitoring_interval_seconds: number;
  cpu_warning_percent: number;
  memory_warning_percent: number;
  disk_warning_percent: number;
  response_time_warning_ms: number;
  error_rate_warning_percent: number;
  availability_warning_percent: number;
  updated_at: string;
}

export interface ServiceDependency {
  upstream_service_id: string;
  downstream_service_id: string;
}

export interface IncidentAnalysis {
  incident: Incident;
  analysis: RCAResult;
}
