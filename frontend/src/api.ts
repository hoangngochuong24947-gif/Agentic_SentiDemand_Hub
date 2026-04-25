import type {
  ApiHealth,
  DeepSeekSessionResponse,
  InsightResponse,
  ManifestResponse,
  RebuildStatus,
  RunArtifact,
  RunRecord,
  UploadResponse
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

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

export const api = {
  health: async (): Promise<ApiHealth> => ({
    status: "ok",
    service: "SentiDemand Hub",
    version: "phase-1",
    checkedAt: new Date().toISOString()
  }),

  listRuns: async (): Promise<RunRecord[]> => {
    const payload = await request<ManifestResponse>("/api/manifest");
    return (payload.runs ?? []).map(normalizeRun);
  },

  getRun: async (runId: string): Promise<RunRecord> => {
    const payload = await request<RunRecord>(`/api/runs/${encodeURIComponent(runId)}`);
    return normalizeRun(payload);
  },

  uploadRun: async (file: File): Promise<UploadResponse> => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResponse>("/upload", {
      method: "POST",
      body: form
    });
  },

  saveDeepSeekKey: async (apiKey: string): Promise<DeepSeekSessionResponse> =>
    request<DeepSeekSessionResponse>("/api/session/deepseek-key", withJson({ api_key: apiKey })),

  generateInsight: async (runId: string, sessionId: string): Promise<InsightResponse> =>
    request<InsightResponse>(
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
