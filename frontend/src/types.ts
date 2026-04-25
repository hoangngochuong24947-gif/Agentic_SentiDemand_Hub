import type { ReactNode } from "react";

export type RunStatus = "completed" | "failed" | "processing" | "queued" | "unknown";
export type ArtifactStatus = "ready" | "missing" | "failed" | "unknown";
export type ArtifactKind = "table" | "chart" | "log" | "insight" | "file";
export type RebuildPhaseStatus = "planned" | "in_progress" | "blocked" | "done";

export interface ApiHealth {
  status: "ok" | "degraded" | "error" | "unknown";
  service?: string;
  version?: string;
  checkedAt?: string;
  detail?: string;
}

export interface ArtifactPreview {
  columns?: string[];
  rows?: Array<Record<string, unknown>>;
  lines?: string[];
  file?: string;
}

export interface RunArtifact {
  type?: ArtifactKind | string;
  name: string;
  title?: string;
  summary?: string;
  status?: ArtifactStatus | string;
  reason?: string;
  path?: string;
  downloadable?: boolean;
  preview?: ArtifactPreview;
  chart_id?: string;
  chart_type?: string;
  open_url?: string;
  download_url?: string;
}

export interface RunSummaryMetrics {
  chart_count?: number;
  total_chart_slots?: number;
  saved_file_count?: number;
  log_file_count?: number;
}

export interface RunRecord {
  run_id: string;
  source_file?: string;
  created_at?: string;
  status?: RunStatus | string;
  user_message?: string;
  summary?: RunSummaryMetrics;
  derived_tables?: RunArtifact[];
  logs?: RunArtifact[];
  charts?: RunArtifact[];
  chart_failures?: string[];
  insight_status?: string;
  insight_updated_at?: string;
  insights?: RunArtifact[];
}

export interface ManifestResponse {
  version?: string;
  total_runs?: number;
  runs?: RunRecord[];
}

export interface UploadResponse {
  uploaded_file: string;
  run_id: string;
  status: string;
  user_message?: string;
  artifacts?: {
    derived_tables?: number;
    logs?: number;
    charts?: number;
    missing_charts?: number;
  };
  routes?: {
    tables?: string;
    dashboard?: string;
    insights?: string;
    legacy?: string;
  };
}

export interface DeepSeekSessionResponse {
  session_id: string;
  masked_key: string;
  status: string;
}

export interface InsightResponse {
  run_id: string;
  insight_status: string;
  insight_updated_at?: string;
  advice_markdown?: string;
  artifacts?: RunArtifact[];
}

export interface RebuildStatus {
  phase: string;
  status: RebuildPhaseStatus;
  progress: number;
  summary: string;
  completed: string[];
  next: string;
}

export interface TableColumn<TData extends object> {
  key: keyof TData | string;
  header: string;
  align?: "left" | "center" | "right";
  width?: string;
  render?: (row: TData, rowIndex: number) => ReactNode;
}
