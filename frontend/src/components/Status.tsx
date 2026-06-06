import { AlertCircle, CheckCircle2, Clock, Loader2 } from "lucide-react";
import type { RebuildStatus } from "../types";

type Tone = "neutral" | "success" | "warning" | "danger";

export function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return <span className={`status-badge ${tone}`}>{label}</span>;
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="state-box">
      <Loader2 className="spin" size={20} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="state-box empty">
      <Clock size={22} aria-hidden="true" />
      <strong>{title}</strong>
      {description ? <span>{description}</span> : null}
    </div>
  );
}

export function ErrorState({ title = "Request failed", error }: { title?: string; error?: unknown }) {
  const message = error instanceof Error ? error.message : "Please try again.";
  return (
    <div className="state-box error">
      <AlertCircle size={22} aria-hidden="true" />
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
  );
}

export function RebuildProgress({ status }: { status: RebuildStatus }) {
  const progress = Math.max(0, Math.min(100, status.progress));
  return (
    <article className="panel compact-panel">
      <div className="progress-head">
        <div className="progress-stage">
          {status.status === "done" ? (
            <CheckCircle2 size={20} aria-hidden="true" />
          ) : (
            <Loader2 className="spin" size={20} aria-hidden="true" />
          )}
          <strong>{status.phase}</strong>
        </div>
        <StatusBadge label={status.status} tone={status.status === "done" ? "success" : "warning"} />
      </div>
      <div className="progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <p>{status.summary}</p>
      <span className="muted">Next: {status.next}</span>
    </article>
  );
}
