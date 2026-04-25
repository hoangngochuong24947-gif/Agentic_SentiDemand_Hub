import { useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { BarChart3, Brain, Database, FileText, ListChecks, Upload } from "lucide-react";
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
import {
  useDeepSeekSession,
  useGenerateInsight,
  useRebuildProgress,
  useRun,
  useRunCharts,
  useRunLogs,
  useRuns,
  useRunTables,
  useUploadRun
} from "./hooks";
import type { RunArtifact, RunRecord } from "./types";

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

function UploadPage() {
  const runs = useRuns();
  const uploadRun = useUploadRun();
  const rebuild = useRebuildProgress();
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  async function submitUpload() {
    if (!selectedFile) return;
    const payload = await uploadRun.mutateAsync(selectedFile);
    navigate(`/workspace/${payload.run_id}`);
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
          <button className="primary-button" disabled={!selectedFile || uploadRun.isPending} onClick={submitUpload}>
            {uploadRun.isPending ? "Analyzing" : "Analyze"}
          </button>
          {uploadRun.isError ? <ErrorState title="Upload failed" error={uploadRun.error} /> : null}
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
    <Layout eyebrow="Tables" title={getRunTitle(tables.run)} subtitle="Searchable previews and file actions.">
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
  return (
    <Layout eyebrow="Charts" title={getRunTitle(charts.run)} subtitle="HTML chart artifacts are reused in Phase 1.">
      {charts.isLoading ? (
        <LoadingState />
      ) : charts.isError ? (
        <ErrorState error={charts.error} />
      ) : charts.data.length ? (
        <div className="chart-grid">
          {charts.data.map((chart) => (
            <ChartCard key={`${chart.name}-${chart.open_url || chart.reason}`} chart={chart} />
          ))}
        </div>
      ) : (
        <EmptyState title="No charts" />
      )}
    </Layout>
  );
}

function AdviceBlocks({ markdown }: { markdown?: string }) {
  if (!markdown) {
    return <EmptyState title="No advice yet" description="Save a key and generate advice." />;
  }
  return (
    <div className="advice-grid">
      {["Findings", "Actions", "Risks"].map((title) => (
        <article className="advice-block" key={title}>
          <h3>{title}</h3>
          <pre>{markdown}</pre>
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
  const markdown = generate.data?.advice_markdown;

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
      <AdviceBlocks markdown={markdown} />
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
    <Layout eyebrow="Runs" title={getRunTitle(run.data)} subtitle="Legacy replacement audit view.">
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
