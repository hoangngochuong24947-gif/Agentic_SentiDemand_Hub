import { Download, ExternalLink, FileText } from "lucide-react";
import type { RunArtifact } from "../types";
import { StatusBadge } from "./Status";

export function ArtifactActions({ artifact }: { artifact: RunArtifact }) {
  return (
    <div className="inline-actions">
      {artifact.open_url ? (
        <a href={artifact.open_url} target="_blank" rel="noreferrer" aria-label={`Open ${artifact.title || artifact.name}`}>
          <ExternalLink size={16} aria-hidden="true" />
        </a>
      ) : null}
      {artifact.download_url ? (
        <a href={artifact.download_url} aria-label={`Download ${artifact.title || artifact.name}`}>
          <Download size={16} aria-hidden="true" />
        </a>
      ) : null}
    </div>
  );
}

export function ArtifactCard({ artifact, children }: { artifact: RunArtifact; children?: React.ReactNode }) {
  const status = artifact.status || "unknown";
  const tone = status === "ready" ? "success" : status === "missing" || status === "failed" ? "danger" : "neutral";

  return (
    <article className="artifact-card">
      <header className="artifact-head">
        <div className="artifact-title">
          <FileText size={17} aria-hidden="true" />
          <div>
            <h3>{artifact.title || artifact.name}</h3>
            {artifact.summary ? <p>{artifact.summary}</p> : null}
          </div>
        </div>
        <StatusBadge label={String(status)} tone={tone} />
      </header>
      {children}
      {artifact.reason ? <div className="missing-note">{artifact.reason}</div> : null}
      <ArtifactActions artifact={artifact} />
    </article>
  );
}
