import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getArtifactGroups } from "./api";

const SESSION_STORAGE_KEY = "sentidemand-deepseek-session-id";

export const queryKeys = {
  health: ["health"] as const,
  runs: ["runs"] as const,
  run: (runId: string) => ["runs", runId] as const,
  runChartData: (runId: string) => ["runs", runId, "chartData"] as const,
  analysisJob: (jobId: string) => ["analysisJob", jobId] as const,
  exportResults: (runId: string) => ["runs", runId, "export"] as const,
  rebuildStatus: ["rebuildStatus"] as const
};

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: api.health,
    retry: 1
  });
}

export function useRuns() {
  return useQuery({
    queryKey: queryKeys.runs,
    queryFn: api.listRuns
  });
}

export function useRun(runId?: string) {
  return useQuery({
    queryKey: queryKeys.run(runId ?? ""),
    queryFn: () => api.getRun(runId ?? ""),
    enabled: Boolean(runId)
  });
}

export function useRunTables(runId?: string) {
  const run = useRun(runId);
  const tables = useMemo(() => getArtifactGroups(run.data).tables, [run.data]);
  return { ...run, data: tables, run: run.data };
}

export function useRunCharts(runId?: string) {
  const run = useRun(runId);
  const charts = useMemo(() => getArtifactGroups(run.data).charts, [run.data]);
  return { ...run, data: charts, run: run.data };
}

export function useStructuredRunCharts(runId?: string) {
  return useQuery({
    queryKey: queryKeys.runChartData(runId ?? ""),
    queryFn: () => api.getRunChartData(runId ?? ""),
    enabled: Boolean(runId),
    retry: false
  });
}

export function useRunLogs(runId?: string) {
  const run = useRun(runId);
  const logs = useMemo(() => getArtifactGroups(run.data).logs, [run.data]);
  return { ...run, data: logs, run: run.data };
}

export function useUploadRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.uploadRun,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.runs });
    }
  });
}

export function useAnalysisJob(jobId?: string) {
  return useQuery({
    queryKey: queryKeys.analysisJob(jobId ?? ""),
    queryFn: () => api.getAnalysisJob(jobId ?? ""),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1200;
    },
    retry: 2
  });
}

export function useCancelAnalysisJob(jobId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.cancelAnalysisJob(jobId ?? ""),
    onSuccess: async () => {
      if (jobId) {
        await queryClient.invalidateQueries({ queryKey: queryKeys.analysisJob(jobId) });
      }
    }
  });
}

export function useExportResults(runId?: string) {
  return useMutation({
    mutationKey: queryKeys.exportResults(runId ?? ""),
    mutationFn: () => api.exportResults(runId ?? "")
  });
}

export function useDeepSeekSession() {
  return useMutation({
    mutationFn: api.saveDeepSeekKey,
    onSuccess: (payload) => {
      window.localStorage.setItem(SESSION_STORAGE_KEY, payload.session_id);
    }
  });
}

export function getDeepSeekSessionId() {
  return window.localStorage.getItem(SESSION_STORAGE_KEY) ?? "";
}

export function useGenerateInsight(runId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.generateInsight(runId ?? "", getDeepSeekSessionId()),
    onSuccess: async () => {
      if (runId) {
        await queryClient.invalidateQueries({ queryKey: queryKeys.run(runId) });
      }
    }
  });
}

export function useRebuildProgress() {
  return useQuery({
    queryKey: queryKeys.rebuildStatus,
    queryFn: api.getRebuildStatus,
    staleTime: 60_000
  });
}

export function useFeatureFlag(name: string) {
  const flags: Record<string, boolean> = {
    apiV1: !["0", "false", "off"].includes(String(import.meta.env.VITE_USE_API_V1 ?? "true").toLowerCase()),
    iframeCharts: true,
    asyncUpload: false,
    structuredAdvice: true
  };
  return Boolean(flags[name]);
}
