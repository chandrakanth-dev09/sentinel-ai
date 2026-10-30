import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  { to: "/", label: "Overview", icon: "◫", end: true },
  { to: "/services", label: "Services", icon: "▣" },
  { to: "/dependencies", label: "Dependency map", icon: "⤳" },
  { to: "/incidents", label: "Incidents", icon: "⚑" },
  { to: "/rca", label: "Root cause", icon: "⌕" },
  { to: "/logs", label: "Log explorer", icon: "≡" },
  { to: "/model", label: "Model", icon: "◎" },
  { to: "/settings", label: "Settings", icon: "⚙" }
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">S</div>
          <div><strong>SentinelAI</strong><span>OPERATIONS CENTER</span></div>
        </div>
        <nav className="primary-nav" aria-label="Primary navigation">
          <span className="nav-section">WORKSPACE</span>
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="live-dot" /> Monitoring workspace
          <small>API-backed telemetry</small>
        </div>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <div className="breadcrumb">SentinelAI <span>/</span> Observability</div>
          <div className="topbar-right"><span className="live-indicator"><i /> API-backed views</span></div>
        </header>
        <main className="page-content"><Outlet /></main>
      </div>
    </div>
  );
}
