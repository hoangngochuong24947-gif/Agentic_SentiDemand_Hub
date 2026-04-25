import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getArtifactGroups } from "./api";

const SESSION_STORAGE_KEY = "sentidemand-deepseek-session-id";

export const queryKeys = {
  health: ["health"] as const,
  runs: ["runs"] as const,
  run: (runId: string) => ["runs", runId] as const,
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
    iframeCharts: true,
    asyncUpload: false,
    structuredAdvice: false
  };
  return Boolean(flags[name]);
}
