import type { ReactNode } from "react";

export function LoadingState({ label = "Loading data…" }: { label?: string }) {
  return <div className="feedback loading-state" role="status"><span className="spinner" />{label}</div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="feedback error-state" role="alert">
      <div><strong>Unable to load this view</strong><p>{message}</p></div>
      <button className="button button-secondary" onClick={onRetry}>Retry</button>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="feedback empty-state"><strong>{title}</strong>{children && <p>{children}</p>}</div>;
}

export function PageHeader({ title, subtitle, action }: {
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return <div className="page-header"><div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>;
}

export function StatCard({ label, value, detail, tone = "neutral" }: {
  label: string;
  value: string | number;
  detail?: string;
  tone?: "neutral" | "good" | "warning" | "danger";
}) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {detail && <span className="stat-detail">{detail}</span>}
    </article>
  );
}

export function StatusPill({ value }: { value: string }) {
  const className = value.toLowerCase().replaceAll("_", "-").replaceAll(" ", "-");
  return <span className={`pill pill-${className}`}>{value.replaceAll("_", " ")}</span>;
}

export function SourcePill({ source }: { source: string }) {
  return <span className={`source-pill source-${source.toLowerCase()}`}>{source}</span>;
}
