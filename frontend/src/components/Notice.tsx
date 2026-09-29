import type { ReactNode } from "react";
import { describeError } from "../api/client";

export function Notice({
  tone = "info",
  title,
  children,
  action,
}: {
  tone?: "info" | "warn" | "error" | "danger";
  title?: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  const role = tone === "error" || tone === "danger" ? "alert" : "status";
  return (
    <div className={`notice notice-${tone}`} role={role}>
      <div className="notice-body">
        {title && <strong>{title}</strong>}
        {children && <div>{children}</div>}
      </div>
      {action && <div className="notice-action">{action}</div>}
    </div>
  );
}

export function ErrorNotice({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { title, detail } = describeError(error);
  return (
    <Notice
      tone="error"
      title={title}
      action={
        onRetry && (
          <button className="btn btn-small" onClick={onRetry}>
            Try again
          </button>
        )
      }
    >
      {detail}
    </Notice>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="spinner-wrap" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function Badge({ tone = "neutral", children, title }: { tone?: "neutral" | "good" | "warn" | "bad" | "sim"; children: ReactNode; title?: string }) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {children}
    </span>
  );
}
