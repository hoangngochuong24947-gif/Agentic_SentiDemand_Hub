import type {
  ApiHealth,
  AnalysisJobCancelResponse,
  AnalysisJobResponse,
  DeepSeekSessionResponse,
  ExportResultsResponse,
  InsightResponse,
  RebuildStatus,
  RunArtifact,
  RunRecord,
  RunResponse,
  RunsResponse,
  StructuredChartData,
  StructuredChartDataResponse,
  UploadResponse
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const USE_API_V1 = !["0", "false", "off"].includes(
  String(import.meta.env.VITE_USE_API_V1 ?? "true").toLowerCase()
);

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function buildUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

async function request<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const response = await fetch(buildUrl(path), init);
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload && "detail" in payload
        ? String((payload as { detail?: unknown }).detail)
        : response.statusText;
    throw new ApiError(detail, response.status, payload);
  }

  return payload as TResponse;
}

async function requestWithV1Fallback<TResponse>(
  v1Path: string,
  legacyPath: string,
  init?: RequestInit | (() => RequestInit)
): Promise<TResponse> {
  const makeInit = () => (typeof init === "function" ? init() : init);

  if (!USE_API_V1) {
    return request<TResponse>(legacyPath, makeInit());
  }

  try {
    return await request<TResponse>(v1Path, makeInit());
  } catch {
    return request<TResponse>(legacyPath, makeInit());
  }
}

function withJson(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  };
}

function withArtifactLinks(runId: string, artifactType: "tables" | "logs" | "charts", artifacts: RunArtifact[] = []) {
  let fileIndex = 0;
  return artifacts.map((artifact) => {
    if (artifact.open_url || !artifact.path) return artifact;
    const index = fileIndex;
    fileIndex += 1;
    return {
      ...artifact,
      open_url: `/runs/${encodeURIComponent(runId)}/artifacts/${artifactType}/${index}`,
      download_url: `/runs/${encodeURIComponent(runId)}/artifacts/${artifactType}/${index}?download=true`
    };
  });
}

function normalizeRun(raw: RunRecord): RunRecord {
  const runId = String(raw.run_id || "");
  return {
    ...raw,
    run_id: runId,
    status: raw.status || "unknown",
    derived_tables: withArtifactLinks(runId, "tables", raw.derived_tables ?? []),
    logs: withArtifactLinks(runId, "logs", raw.logs ?? []),
    charts: withArtifactLinks(runId, "charts", raw.charts ?? []),
    insights: raw.insights ?? []
  };
}

function normalizeRunsResponse(payload: RunsResponse): RunRecord[] {
  const runs = Array.isArray(payload) ? payload : payload.runs ?? [];
  return runs.map(normalizeRun);
}

function normalizeRunResponse(payload: RunRecord | RunResponse): RunRecord {
  return normalizeRun("run" in payload && payload.run ? payload.run : (payload as RunRecord));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeStructuredChartData(payload: StructuredChartDataResponse | StructuredChartData[] | unknown): StructuredChartData[] {
  if (Array.isArray(payload)) {
    return payload.filter(isRecord) as StructuredChartData[];
  }
  if (!isRecord(payload)) return [];

  const candidates = [payload.charts, payload.chart_data, payload.data];
  const list = candidates.find(Array.isArray);
  if (Array.isArray(list)) {
    return list.filter(isRecord) as StructuredChartData[];
  }

  if ("kind" in payload || "chart_type" in payload || "type" in payload) {
    return [payload as StructuredChartData];
  }
  return [];
}

export const api = {
  health: async (): Promise<ApiHealth> => {
    if (USE_API_V1) {
      try {
        return {
          ...(await request<ApiHealth>("/api/v1/health")),
          checkedAt: new Date().toISOString()
        };
      } catch {
        // Fall through to the legacy health approximation below.
      }
    }
    await request<unknown>("/api/manifest");
    return {
      status: "ok",
      service: "SentiDemand Hub",
      version: "legacy",
      checkedAt: new Date().toISOString()
    };
  },

  listRuns: async (): Promise<RunRecord[]> => {
    const payload = await requestWithV1Fallback<RunsResponse>("/api/v1/runs", "/api/manifest");
    return normalizeRunsResponse(payload);
  },

  getRun: async (runId: string): Promise<RunRecord> => {
    const encodedRunId = encodeURIComponent(runId);
    const payload = await requestWithV1Fallback<RunRecord | RunResponse>(
      `/api/v1/runs/${encodedRunId}`,
      `/api/runs/${encodedRunId}`
    );
    return normalizeRunResponse(payload);
  },

  uploadRun: async (file: File): Promise<UploadResponse> => {
    return requestWithV1Fallback<UploadResponse>("/api/v1/data/upload", "/upload", () => {
      const form = new FormData();
      form.append("file", file);
      return {
        method: "POST",
        body: form
      };
    });
  },

  getAnalysisJob: async (jobId: string): Promise<AnalysisJobResponse> =>
    request<AnalysisJobResponse>(`/api/v1/analysis/jobs/${encodeURIComponent(jobId)}`),

  cancelAnalysisJob: async (jobId: string): Promise<AnalysisJobCancelResponse> =>
    request<AnalysisJobCancelResponse>(`/api/v1/analysis/jobs/${encodeURIComponent(jobId)}/cancel`, {
      method: "POST"
    }),

  exportResults: async (runId: string): Promise<ExportResultsResponse> =>
    request<ExportResultsResponse>("/api/v1/export/results", withJson({ run_id: runId })),

  getRunChartData: async (runId: string): Promise<StructuredChartData[]> => {
    if (!USE_API_V1) return [];
    try {
      const payload = await request<StructuredChartDataResponse | StructuredChartData[]>(
        `/api/v1/runs/${encodeURIComponent(runId)}/chart-data`
      );
      return normalizeStructuredChartData(payload);
    } catch {
      return [];
    }
  },

  saveDeepSeekKey: async (apiKey: string): Promise<DeepSeekSessionResponse> =>
    request<DeepSeekSessionResponse>("/api/session/deepseek-key", withJson({ api_key: apiKey })),

  generateInsight: async (runId: string, sessionId: string): Promise<InsightResponse> =>
    requestWithV1Fallback<InsightResponse>(
      `/api/v1/runs/${encodeURIComponent(runId)}/insights/generate`,
      `/api/runs/${encodeURIComponent(runId)}/insights/generate`,
      withJson({ session_id: sessionId })
    ),

  getRebuildStatus: async (): Promise<RebuildStatus> => ({
    phase: "Phase 1",
    status: "in_progress",
    progress: 45,
    summary: "React shell is connected to the current Hub endpoints.",
    completed: ["Phase 0 docs", "React/Vite foundation", "Current endpoint adapter"],
    next: "Finish route screens, verify build, then begin /api/v1 extraction."
  })
};

export function getArtifactGroups(run?: RunRecord) {
  return {
    tables: (run?.derived_tables ?? []) as RunArtifact[],
    charts: (run?.charts ?? []) as RunArtifact[],
    logs: (run?.logs ?? []) as RunArtifact[],
    insights: (run?.insights ?? []) as RunArtifact[]
  };
}

export function getRunTitle(run?: RunRecord): string {
  return run?.source_file || run?.run_id || "Untitled run";
}
