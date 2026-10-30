import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { LoadingState } from "./components/Feedback";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const DependencyMapPage = lazy(() => import("./pages/DependencyMapPage").then((module) => ({ default: module.DependencyMapPage })));
const IncidentDetailPage = lazy(() => import("./pages/IncidentsPage").then((module) => ({ default: module.IncidentDetailPage })));
const IncidentsPage = lazy(() => import("./pages/IncidentsPage").then((module) => ({ default: module.IncidentsPage })));
const LogsPage = lazy(() => import("./pages/LogsPage").then((module) => ({ default: module.LogsPage })));
const ModelPage = lazy(() => import("./pages/ModelPage").then((module) => ({ default: module.ModelPage })));
const RCAPage = lazy(() => import("./pages/RCAPage").then((module) => ({ default: module.RCAPage })));
const ServiceDetailPage = lazy(() => import("./pages/ServicesPage").then((module) => ({ default: module.ServiceDetailPage })));
const ServicesPage = lazy(() => import("./pages/ServicesPage").then((module) => ({ default: module.ServicesPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })));

export default function App() {
  return (
    <Suspense fallback={<LoadingState label="Loading workspace…" />}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="services" element={<ServicesPage />} />
          <Route path="services/:serviceId" element={<ServiceDetailPage />} />
          <Route path="dependencies" element={<DependencyMapPage />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="incidents/:incidentId" element={<IncidentDetailPage />} />
          <Route path="rca" element={<RCAPage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="model" element={<ModelPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
