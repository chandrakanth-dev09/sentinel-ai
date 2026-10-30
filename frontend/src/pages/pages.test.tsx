import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";
import { IncidentDetailPage, IncidentsPage } from "./IncidentsPage";
import { analyzeIncident, getAnomalyHistory, getIncident, getIncidents, getMetrics, getOverview, updateIncident } from "../services/api";
import type { Incident, Overview } from "../types";

vi.mock("../services/api", () => ({
  analyzeIncident: vi.fn(),
  getAnomalyHistory: vi.fn(),
  getIncident: vi.fn(),
  getIncidents: vi.fn(),
  getMetrics: vi.fn(),
  getOverview: vi.fn(),
  updateIncident: vi.fn(),
  getErrorMessage: (error: unknown) => error instanceof Error ? error.message : "Request failed"
}));

const incident: Incident = {
  id: "incident-1",
  title: "Elevated API latency",
  description: "Response time exceeded the configured threshold.",
  severity: "HIGH",
  status: "OPEN",
  root_cause_service_id: null,
  root_cause_service_name: null,
  affected_services: ["api-service"],
  first_detected_at: "2025-01-01T10:00:00Z",
  last_updated_at: "2025-01-01T10:00:00Z",
  resolved_at: null,
  explanation: null,
  recommended_actions: null,
  evidence: []
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("monitoring pages", () => {
  it("renders overview data returned by the API", async () => {
    const overview: Overview = {
      total_services: 2,
      healthy_services: 1,
      degraded_services: 1,
      critical_services: 0,
      unknown_services: 0,
      active_incidents: 1,
      anomalies_last_24_hours: 3,
      availability_percent: 99.5,
      recent_incidents: []
    };
    vi.mocked(getOverview).mockResolvedValue(overview);
    vi.mocked(getMetrics).mockResolvedValue([]);
    vi.mocked(getAnomalyHistory).mockResolvedValue({ total: 0, items: [] });

    render(<MemoryRouter><DashboardPage /></MemoryRouter>);

    expect(await screen.findByText("Monitored services")).toBeInTheDocument();
    expect(screen.getByText("99.50%")).toBeInTheDocument();
    expect(screen.getByText("No incidents recorded")).toBeInTheDocument();
  });

  it("shows a clear error when the dashboard API request fails", async () => {
    vi.mocked(getOverview).mockRejectedValue(new Error("API unavailable"));
    vi.mocked(getMetrics).mockResolvedValue([]);
    vi.mocked(getAnomalyHistory).mockResolvedValue({ total: 0, items: [] });

    render(<MemoryRouter><DashboardPage /></MemoryRouter>);

    expect(await screen.findByRole("alert")).toHaveTextContent("API unavailable");
  });

  it("filters incidents and opens the lifecycle detail actions", async () => {
    vi.mocked(getIncidents).mockResolvedValue([incident]);
    vi.mocked(getIncident).mockResolvedValue(incident);
    vi.mocked(updateIncident).mockResolvedValue({ ...incident, status: "INVESTIGATING" });
    vi.mocked(analyzeIncident).mockResolvedValue({ incident, analysis: {
      analysis_start: incident.first_detected_at,
      analysis_end: incident.last_updated_at,
      probable_root_cause: null,
      affected_services: [],
      incident_timeline: [],
      supporting_evidence: [],
      alternative_causes: [],
      recommended_investigation_steps: [],
      ranking_method: "test"
    } });

    const { unmount } = render(
      <MemoryRouter initialEntries={["/incidents"]}>
        <Routes>
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("Elevated API latency")).toBeInTheDocument();
    expect(getIncidents).toHaveBeenCalledWith({ status: undefined, severity: undefined });
    fireEvent.change(screen.getByLabelText("Filter by status"), { target: { value: "OPEN" } });
    await waitFor(() => expect(getIncidents).toHaveBeenCalledWith({ status: "OPEN", severity: undefined }));

    unmount();
    render(
      <MemoryRouter initialEntries={["/incidents/incident-1"]}>
        <Routes><Route path="/incidents/:incidentId" element={<IncidentDetailPage />} /></Routes>
      </MemoryRouter>
    );
    expect(await screen.findByText("Reanalyze incident")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Update incident status"), { target: { value: "INVESTIGATING" } });
    await waitFor(() => expect(updateIncident).toHaveBeenCalledWith("incident-1", { status: "INVESTIGATING" }));
    fireEvent.click(screen.getByRole("button", { name: "Reanalyze incident" }));
    await waitFor(() => expect(analyzeIncident).toHaveBeenCalledWith("incident-1"));
  });
});
