import axios from "axios";
import type {
  AnomalyHistory,
  AppConfiguration,
  ApplicationLog,
  DependencyGraph,
  Incident,
  IncidentAnalysis,
  Metric,
  ModelStatus,
  Overview,
  RCAResult,
  Service,
  ServiceDependency
} from "../types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
  ?? (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "");

export const isApiConfigured = Boolean(apiBaseUrl) || import.meta.env.DEV;

const api = axios.create({
  baseURL: apiBaseUrl || undefined,
  timeout: 15000,
  headers: { "Content-Type": "application/json" }
});

export const getOverview = async (): Promise<Overview> =>
  (await api.get<Overview>("/overview")).data;

export const getMetrics = async (): Promise<Metric[]> =>
  (await api.get<Metric[]>("/metrics", { params: { limit: 2000 } })).data;

export const getServices = async (): Promise<Service[]> =>
  (await api.get<Service[]>("/services/monitoring")).data;

export const getService = async (serviceId: string): Promise<Service> =>
  (await api.get<Service>(`/services/${serviceId}`)).data;

export const getServiceMetrics = async (serviceId: string): Promise<Metric[]> =>
  (await api.get<Metric[]>("/metrics", { params: { service_id: serviceId, limit: 2000 } })).data;

export const getDependencyGraph = async (): Promise<DependencyGraph> =>
  (await api.get<DependencyGraph>("/services/dependency-graph")).data;

export const getIncidents = async (params: {
  status?: string;
  severity?: string;
  service_id?: string;
} = {}): Promise<Incident[]> => (await api.get<Incident[]>("/incidents", { params })).data;

export const getIncident = async (incidentId: string): Promise<Incident> =>
  (await api.get<Incident>(`/incidents/${incidentId}`)).data;

export const updateIncident = async (
  incidentId: string,
  changes: { status?: string; severity?: string }
): Promise<Incident> =>
  (await api.patch<Incident>(`/incidents/${incidentId}`, changes)).data;

export const analyzeIncident = async (incidentId: string): Promise<IncidentAnalysis> =>
  (await api.post<IncidentAnalysis>(`/incidents/${incidentId}/analyze`)).data;

export const analyzeRootCause = async (
  lookbackMinutes: number,
  serviceId?: string
): Promise<RCAResult> =>
  (await api.post<RCAResult>("/incidents/analyze", {
    lookback_minutes: lookbackMinutes,
    service_ids: serviceId ? [serviceId] : undefined
  })).data;

export const getLogs = async (params: {
  service_id?: string;
  level?: string;
  search?: string;
  since?: string;
  until?: string;
} = {}): Promise<ApplicationLog[]> =>
  (await api.get<ApplicationLog[]>("/logs", { params })).data;

export const getModelStatus = async (): Promise<ModelStatus> =>
  (await api.get<ModelStatus>("/ml/model-status")).data;

export const getAnomalyHistory = async (): Promise<AnomalyHistory> =>
  (await api.get<AnomalyHistory>("/ml/anomaly-history", { params: { limit: 500 } })).data;

export const getConfiguration = async (): Promise<AppConfiguration> =>
  (await api.get<AppConfiguration>("/settings")).data;

export const updateConfiguration = async (
  updates: Partial<Omit<AppConfiguration, "updated_at">>
): Promise<AppConfiguration> =>
  (await api.patch<AppConfiguration>("/settings", updates)).data;

export const registerService = async (service: {
  name: string;
  description?: string;
  is_simulated: boolean;
}): Promise<Service> => (await api.post<Service>("/services", service)).data;

export const registerDependency = async (
  dependency: ServiceDependency
): Promise<ServiceDependency> =>
  (await api.post<ServiceDependency>("/services/dependencies", dependency)).data;

export function getErrorMessage(error: unknown): string {
  if (!isApiConfigured) {
    return "This GitHub Pages site hosts the interface only. Deploy the SentinelAI API and set VITE_API_BASE_URL to enable live data and actions.";
  }
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (!error.response) return "Cannot reach the SentinelAI API. Check that the backend is running.";
    return `The API request failed (${error.response.status}).`;
  }
  return error instanceof Error ? error.message : "An unexpected error occurred.";
}
