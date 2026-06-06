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
  advice_markdown?: string;
  structured_advice?: StructuredAdvice;
  insights?: RunArtifact[];
}

export interface ManifestResponse {
  version?: string;
  total_runs?: number;
  runs?: RunRecord[];
}

export type RunsResponse = ManifestResponse | RunRecord[];

export interface RunResponse {
  run?: RunRecord;
}

export interface UploadResponse {
  job_id?: string;
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

export interface AnalysisJobResponse {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed" | string;
  run_id?: string;
  kind?: string;
  created_at?: string;
  updated_at?: string;
  progress?: number;
  steps?: Array<string | AnalysisJobStep>;
  message?: string;
  result?: Record<string, unknown>;
  error?: string | null;
  cancellation_requested?: boolean;
  retry_of?: string | null;
}

export interface AnalysisJobCancelResponse {
  job_id: string;
  status: string;
  cancellation_requested?: boolean;
  message?: string;
}

export interface AnalysisJobStep {
  name?: string;
  label?: string;
  status?: string;
  progress?: number;
  message?: string;
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
  structured_advice?: StructuredAdvice;
  artifacts?: RunArtifact[];
}

export interface ExportResultsResponse {
  run_id?: string;
  status?: string;
  message?: string;
  path?: string;
  open_url?: string;
  download_url?: string;
}

export type StructuredAdviceSection =
  | string
  | string[]
  | Array<{ title?: string; text?: string; detail?: string; rationale?: string; priority?: string }>;

export interface StructuredAdvice {
  findings?: StructuredAdviceSection;
  actions?: StructuredAdviceSection;
  risks?: StructuredAdviceSection;
  context?: StructuredAdviceSection;
  [section: string]: StructuredAdviceSection | undefined;
}

export type StructuredChartKind = "donut" | "bar" | "lollipop" | "radar" | "summary" | string;

export interface StructuredChartPoint {
  label?: string;
  name?: string;
  category?: string;
  value?: number | string;
  score?: number | string;
  count?: number | string;
  percent?: number | string;
  [key: string]: unknown;
}

export interface StructuredChartSeries {
  name?: string;
  label?: string;
  value?: number | string;
  values?: Array<number | string>;
  data?: StructuredChartPoint[] | Array<number | string>;
  points?: StructuredChartPoint[];
}

export interface StructuredChartData {
  id?: string;
  chart_id?: string;
  name?: string;
  title?: string;
  summary?: string;
  kind?: StructuredChartKind;
  type?: StructuredChartKind;
  chart_type?: StructuredChartKind;
  status?: ArtifactStatus | string;
  labels?: string[];
  values?: Array<number | string>;
  data?: StructuredChartPoint[] | Record<string, unknown>;
  points?: StructuredChartPoint[];
  series?: StructuredChartSeries[];
  metrics?: Record<string, unknown>;
  open_url?: string;
  download_url?: string;
}

export interface StructuredChartDataResponse {
  run_id?: string;
  charts?: StructuredChartData[];
  chart_data?: StructuredChartData[];
  data?: StructuredChartData[];
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
