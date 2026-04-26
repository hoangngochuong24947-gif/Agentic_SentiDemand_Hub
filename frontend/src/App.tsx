import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { BarChart3, Brain, Download, FileText, ListChecks, Upload, XCircle } from "lucide-react";
import { getRunTitle } from "./api";
import {
  ArtifactCard,
  ArtifactTable,
  ChartCard,
  DataTable,
  EmptyState,
  ErrorState,
  Layout,
  LoadingState,
  RebuildProgress,
  StatusBadge
} from "./components";
import { StructuredChartCard } from "./components/Chart";
import {
  useDeepSeekSession,
  useGenerateInsight,
  useAnalysisJob,
  useCancelAnalysisJob,
  useExportResults,
  useRebuildProgress,
  useRun,
  useRunCharts,
  useRunLogs,
  useRuns,
  useStructuredRunCharts,
  useRunTables,
  useUploadRun
} from "./hooks";
import type { AnalysisJobResponse, ExportResultsResponse, RunArtifact, RunRecord, StructuredAdvice, StructuredAdviceSection } from "./types";

function latestRunId(runs?: RunRecord[]) {
  return runs?.[0]?.run_id;
}

function Metric({ icon: Icon, label, value }: { icon: typeof Upload; label: string; value: string | number }) {
  return (
    <article className="metric-card">
      <Icon size={18} aria-hidden="true" />
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function getExportLink(payload?: ExportResultsResponse) {
  return payload?.download_url || payload?.open_url || payload?.path || "";
}

function ExportRunAction({ runId }: { runId?: string }) {
  const exportResults = useExportResults(runId);
  const exportLink = getExportLink(exportResults.data);

  return (
    <div className="export-action">
      <button
        className="primary-button icon-button"
        disabled={!runId || exportResults.isPending}
        onClick={() => exportResults.mutate()}
        title="Export results"
        aria-label="Export results"
      >
        <Download size={16} aria-hidden="true" />
        <span>{exportResults.isPending ? "Exporting" : "Export"}</span>
      </button>
      {exportResults.isSuccess ? (
        exportLink ? (
          <a href={exportLink} target="_blank" rel="noreferrer">
            Open export
          </a>
        ) : (
          <span className="muted">{exportResults.data?.message || "Export ready"}</span>
        )
      ) : null}
      {exportResults.isError ? <span className="quiet-error">Export unavailable</span> : null}
    </div>
  );
}

const uploadSteps = ["Upload", "Clean", "Sentiment", "Topics", "Demand", "Charts"] as const;

function getJobSteps(job?: AnalysisJobResponse) {
  if (!job?.steps?.length) return [...uploadSteps];
  return job.steps.map((step) => (typeof step === "string" ? step : step.label || step.name || "Step"));
}

function getJobStepIndex(job?: AnalysisJobResponse) {
  if (!job) return 0;
  if (typeof job.progress === "number") {
    return Math.ceil((Math.max(0, Math.min(100, job.progress)) / 100) * getJobSteps(job).length);
  }
  if (job.status === "completed") return uploadSteps.length;
  if (job.status === "failed") return Math.max(1, findStepFromText(job.message || job.error || ""));
  return findStepFromText(`${job.message || ""} ${JSON.stringify(job.result || {})}`);
}

function findStepFromText(text: string) {
  const value = text.toLowerCase();
  const matches = [
    ["upload", "accepted", "file"],
    ["clean", "preprocess", "derive", "table"],
    ["sentiment", "model"],
    ["topic", "keyword"],
    ["demand", "correlation", "intensity"],
    ["chart", "visual"]
  ];
  const found = matches.findIndex((keywords) => keywords.some((keyword) => value.includes(keyword)));
  return found < 0 ? 1 : found + 1;
}

function UploadProgress({
  isUploading,
  job,
  error,
  onCancel,
  isCanceling,
  cancelRequested,
  cancelError
}: {
  isUploading: boolean;
  job?: AnalysisJobResponse;
  error?: unknown;
  onCancel?: () => void;
  isCanceling?: boolean;
  cancelRequested?: boolean;
  cancelError?: unknown;
}) {
  if (!isUploading && !job && !error) return null;

  const steps = getJobSteps(job);
  const completedThrough = isUploading ? 0 : getJobStepIndex(job);
  const activeIndex = job?.status === "completed" ? -1 : Math.min(completedThrough, steps.length - 1);
  const failed = job?.status === "failed" || Boolean(error);
  const canCancel = Boolean(
    onCancel && job?.job_id && ["pending", "queued", "processing", "running", "canceling"].includes(String(job.status))
  );

  return (
    <div className="upload-progress" aria-label="Upload progress">
      {steps.map((step, index) => {
        const state =
          failed && index === activeIndex
            ? "failed"
            : index < completedThrough || job?.status === "completed"
              ? "done"
              : index === activeIndex
                ? "active"
                : "pending";
        return (
          <div className={`upload-step ${state}`} key={step}>
            <span>{index + 1}</span>
            <strong>{step}</strong>
          </div>
        );
      })}
      {job?.message ? <p>{job.message}</p> : null}
      {job?.error ? <p>{job.error}</p> : null}
      {cancelRequested ? <p>Cancel requested.</p> : null}
      {cancelError ? <p className="quiet-error">Cancel unavailable.</p> : null}
      {canCancel ? (
        <button className="cancel-button" disabled={isCanceling || cancelRequested} onClick={onCancel}>
          <XCircle size={15} aria-hidden="true" />
          <span>{cancelRequested ? "Cancel requested" : isCanceling ? "Requesting" : "Cancel analysis"}</span>
        </button>
      ) : null}
    </div>
  );
}

function UploadPage() {
  const runs = useRuns();
  const uploadRun = useUploadRun();
  const rebuild = useRebuildProgress();
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadJobId, setUploadJobId] = useState("");
  const [uploadedRunId, setUploadedRunId] = useState("");
  const [cancelRequested, setCancelRequested] = useState(false);
  const uploadJob = useAnalysisJob(uploadJobId);
  const cancelJob = useCancelAnalysisJob(uploadJobId);
  const isUploadWorking =
    uploadRun.isPending ||
    Boolean(uploadJobId && uploadJob.data?.status !== "completed" && uploadJob.data?.status !== "failed");

  useEffect(() => {
    const job = uploadJob.data;
    const runId = job?.run_id || uploadedRunId;
    if (job?.status === "completed" && runId) {
      navigate(`/workspace/${runId}`);
    }
  }, [navigate, uploadJob.data, uploadedRunId]);

  async function submitUpload() {
    if (!selectedFile) return;
    setUploadJobId("");
    setUploadedRunId("");
    setCancelRequested(false);
    const payload = await uploadRun.mutateAsync(selectedFile);
    if (payload.job_id) {
      setUploadJobId(payload.job_id);
      setUploadedRunId(payload.run_id);
      return;
    }
    navigate(`/workspace/${payload.run_id}`);
  }

  async function requestCancel() {
    if (!uploadJobId) return;
    try {
      await cancelJob.mutateAsync();
      setCancelRequested(true);
    } catch {
      // Mutation state renders the quiet unavailable note.
    }
  }

  return (
    <Layout
      eyebrow="Upload"
      title="SentiDemand"
      subtitle="Review intelligence command center."
      actions={<StatusBadge label="Phase 1" tone="warning" />}
    >
      <section className="home-grid">
        <div className="upload-panel">
          <label className="drop-zone">
            <Upload size={28} aria-hidden="true" />
            <span>{selectedFile ? selectedFile.name : "Drop or select"}</span>
            <small>CSV XLSX XLS JSON</small>
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.json"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <button className="primary-button" disabled={!selectedFile || isUploadWorking} onClick={submitUpload}>
            {isUploadWorking ? "Analyzing" : "Analyze"}
          </button>
          <UploadProgress
            isUploading={uploadRun.isPending}
            job={uploadJob.data}
            error={uploadJob.error}
            onCancel={requestCancel}
            isCanceling={cancelJob.isPending}
            cancelRequested={cancelRequested || Boolean(cancelJob.data?.cancellation_requested)}
            cancelError={cancelJob.error}
          />
          {uploadRun.isError ? <ErrorState title="Upload failed" error={uploadRun.error} /> : null}
          {uploadJob.isError ? <ErrorState title="Job polling failed" error={uploadJob.error} /> : null}
          {uploadJob.data?.status === "failed" ? <ErrorState title="Analysis failed" error={uploadJob.data.error || uploadJob.data.message} /> : null}
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Recent Runs</h2>
            <Link to="/runs">All</Link>
          </div>
          {runs.isLoading ? (
            <LoadingState label="Loading runs" />
          ) : runs.isError ? (
            <ErrorState title="Runs unavailable" error={runs.error} />
          ) : runs.data?.length ? (
            <RunList runs={runs.data.slice(0, 4)} compact />
          ) : (
            <EmptyState title="No runs" description="Upload a file to start." />
          )}
        </div>
      </section>

      <section className="metric-grid">
        <Metric icon={ListChecks} label="Runs" value={runs.data?.length ?? 0} />
        <Metric icon={FileText} label="Tables" value={runs.data?.[0]?.summary?.saved_file_count ?? 0} />
        <Metric icon={BarChart3} label="Charts" value={runs.data?.[0]?.summary?.chart_count ?? 0} />
        <Metric icon={Brain} label="Advice" value={runs.data?.[0]?.insight_status ?? "none"} />
      </section>

      {rebuild.data ? <RebuildProgress status={rebuild.data} /> : null}

      <section className="crawler-strip">
        {["Bilibili", "JD", "Chrome"].map((item) => (
          <article key={item}>{item}</article>
        ))}
      </section>
    </Layout>
  );
}

function RunList({ runs, compact = false }: { runs: RunRecord[]; compact?: boolean }) {
  return (
    <div className={compact ? "run-list compact" : "run-list"}>
      {runs.map((run) => (
        <article className="run-row" key={run.run_id}>
          <div>
            <StatusBadge label={String(run.status || "unknown")} tone={run.status === "completed" ? "success" : run.status === "failed" ? "danger" : "neutral"} />
            <h3>{getRunTitle(run)}</h3>
            <span>{run.created_at || run.run_id}</span>
          </div>
          <div className="row-actions">
            <Link to={`/workspace/${run.run_id}`}>Tables</Link>
            <Link to={`/dashboard/${run.run_id}`}>Charts</Link>
            <Link to={`/insights/${run.run_id}`}>Advice</Link>
          </div>
        </article>
      ))}
    </div>
  );
}

function RunsPage() {
  const runs = useRuns();
  return (
    <Layout eyebrow="Runs" title="Run History" subtitle="Completed analyses and artifacts.">
      {runs.isLoading ? <LoadingState /> : runs.isError ? <ErrorState error={runs.error} /> : runs.data?.length ? <RunList runs={runs.data} /> : <EmptyState title="No runs" />}
    </Layout>
  );
}

function LatestRedirect({ target }: { target: "workspace" | "dashboard" | "insights" | "runs" }) {
  const runs = useRuns();
  if (runs.isLoading) return <LoadingState label="Finding latest run" />;
  const id = latestRunId(runs.data);
  return id ? <Navigate to={`/${target}/${id}`} replace /> : <Navigate to="/" replace />;
}

function WorkspacePage() {
  const { runId } = useParams();
  const runs = useRuns();
  const tables = useRunTables(runId);

  return (
    <Layout
      eyebrow="Tables"
      title={getRunTitle(tables.run)}
      subtitle="Searchable previews and file actions."
      actions={<ExportRunAction runId={runId} />}
    >
      <section className="split-layout">
        <aside className="side-panel">
          <h2>Runs</h2>
          {runs.data?.length ? <RunList runs={runs.data} compact /> : <EmptyState title="No runs" />}
        </aside>
        <div className="content-grid">
          {tables.isLoading ? (
            <LoadingState />
          ) : tables.isError ? (
            <ErrorState error={tables.error} />
          ) : tables.data.length ? (
            tables.data.map((table) => (
              <ArtifactCard key={`${table.name}-${table.open_url}`} artifact={table}>
                <ArtifactTable artifact={table} />
              </ArtifactCard>
            ))
          ) : (
            <EmptyState title="No tables" description="This run has no table artifacts." />
          )}
        </div>
      </section>
    </Layout>
  );
}

function DashboardPage() {
  const { runId } = useParams();
  const charts = useRunCharts(runId);
  const structuredCharts = useStructuredRunCharts(runId);
  const hasStructuredCharts = Boolean(structuredCharts.data?.length);
  const isLoading = charts.isLoading || (structuredCharts.isLoading && !charts.data.length);

  return (
    <Layout
      eyebrow="Charts"
      title={getRunTitle(charts.run)}
      subtitle="Structured charts are used when the API provides them."
      actions={<ExportRunAction runId={runId} />}
    >
      {isLoading ? (
        <LoadingState />
      ) : charts.isError ? (
        <ErrorState error={charts.error} />
      ) : hasStructuredCharts ? (
        <>
          <div className="chart-grid">
            {structuredCharts.data?.map((chart, index) => (
              <StructuredChartCard key={chart.id || chart.chart_id || chart.name || index} chart={chart} />
            ))}
          </div>
          {charts.data.length ? (
            <section className="artifact-section">
              <div className="panel-head">
                <h2>Chart files</h2>
                <span className="muted">Legacy artifacts remain available.</span>
              </div>
              <div className="chart-grid compact-chart-grid">
                {charts.data.map((chart) => (
                  <ChartCard key={`${chart.name}-${chart.open_url || chart.reason}`} chart={chart} />
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : charts.data.length ? (
        <div className="chart-grid">
          {charts.data.map((chart) => (
            <ChartCard key={`${chart.name}-${chart.open_url || chart.reason}`} chart={chart} />
          ))}
        </div>
      ) : (
        <EmptyState title="No charts" description="No structured chart data or chart artifacts were found for this run." />
      )}
    </Layout>
  );
}

function normalizeAdviceSection(section?: StructuredAdviceSection) {
  if (!section) return [];
  if (typeof section === "string") return [section];
  if (Array.isArray(section)) {
    return section
      .map((item) => {
        if (typeof item === "string") return item;
        return [item.title, item.text, item.detail, item.rationale, item.priority].filter(Boolean).join(" - ");
      })
      .filter(Boolean);
  }
  return [];
}

function AdviceBlocks({ markdown, structuredAdvice }: { markdown?: string; structuredAdvice?: StructuredAdvice }) {
  const sections = [
    ["Findings", structuredAdvice?.findings],
    ["Actions", structuredAdvice?.actions],
    ["Risks", structuredAdvice?.risks],
    ["Context", structuredAdvice?.context]
  ] as const;
  const hasStructuredAdvice = sections.some(([, section]) => normalizeAdviceSection(section).length);

  if (!hasStructuredAdvice && !markdown) {
    return <EmptyState title="No advice yet" description="Save a key and generate advice." />;
  }

  return (
    <div className="advice-grid">
      {sections.map(([title, section]) => (
        <article className="advice-block" key={title}>
          <h3>{title}</h3>
          {normalizeAdviceSection(section).length ? (
            <ul>
              {normalizeAdviceSection(section).map((item, index) => (
                <li key={`${title}-${index}`}>{item}</li>
              ))}
            </ul>
          ) : markdown ? (
            <pre>{markdown}</pre>
          ) : (
            <p>No {title.toLowerCase()} supplied.</p>
          )}
        </article>
      ))}
    </div>
  );
}

function InsightsPage() {
  const { runId } = useParams();
  const run = useRun(runId);
  const saveKey = useDeepSeekSession();
  const generate = useGenerateInsight(runId);
  const [apiKey, setApiKey] = useState("");
  const markdown = generate.data?.advice_markdown || run.data?.advice_markdown;
  const structuredAdvice = generate.data?.structured_advice || run.data?.structured_advice;

  return (
    <Layout eyebrow="Advice" title={getRunTitle(run.data)} subtitle="DeepSeek generated decision notes.">
      <section className="insight-controls">
        <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" placeholder="sk-..." aria-label="DeepSeek API Key" />
        <button onClick={() => saveKey.mutate(apiKey)} disabled={!apiKey || saveKey.isPending}>Save</button>
        <button className="primary-button" onClick={() => generate.mutate()} disabled={!runId || generate.isPending}>Generate</button>
        <StatusBadge label={generate.data?.insight_status || run.data?.insight_status || "not_generated"} tone={generate.data?.insight_status === "generated" || run.data?.insight_status === "generated" ? "success" : "neutral"} />
      </section>
      {saveKey.isError ? <ErrorState title="Key failed" error={saveKey.error} /> : null}
      {generate.isError ? <ErrorState title="Advice failed" error={generate.error} /> : null}
      <AdviceBlocks markdown={markdown} structuredAdvice={structuredAdvice} />
    </Layout>
  );
}

function RunDetailPage() {
  const { runId } = useParams();
  const run = useRun(runId);
  const groups = useMemo(() => ({
    tables: run.data?.derived_tables ?? [],
    logs: run.data?.logs ?? [],
    charts: run.data?.charts ?? []
  }), [run.data]);

  function renderList(items: RunArtifact[]) {
    return items.length ? items.slice(0, 6).map((item) => <ArtifactCard key={`${item.name}-${item.open_url}`} artifact={item} />) : <EmptyState title="None" />;
  }

  return (
    <Layout
      eyebrow="Runs"
      title={getRunTitle(run.data)}
      subtitle="Legacy replacement audit view."
      actions={<ExportRunAction runId={runId} />}
    >
      {run.isLoading ? (
        <LoadingState />
      ) : run.isError ? (
        <ErrorState error={run.error} />
      ) : (
        <div className="audit-grid">
          <section><h2>Tables</h2>{renderList(groups.tables)}</section>
          <section><h2>Logs</h2>{renderList(groups.logs)}</section>
          <section><h2>Charts</h2>{renderList(groups.charts)}</section>
        </div>
      )}
    </Layout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<UploadPage />} />
      <Route path="/runs" element={<RunsPage />} />
      <Route path="/workspace" element={<LatestRedirect target="workspace" />} />
      <Route path="/workspace/:runId" element={<WorkspacePage />} />
      <Route path="/dashboard/latest" element={<LatestRedirect target="dashboard" />} />
      <Route path="/dashboard/:runId" element={<DashboardPage />} />
      <Route path="/insights/latest" element={<LatestRedirect target="insights" />} />
      <Route path="/insights/:runId" element={<InsightsPage />} />
      <Route path="/runs/:runId" element={<RunDetailPage />} />
    </Routes>
  );
}
