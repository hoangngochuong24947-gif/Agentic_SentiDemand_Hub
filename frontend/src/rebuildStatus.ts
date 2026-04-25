import type { RebuildStatus } from "./types";

export const initialRebuildStatus: RebuildStatus = {
  phase: "Phase 1",
  status: "in_progress",
  progress: 45,
  summary: "React shell is connected to the current Hub endpoints.",
  completed: ["Phase 0 docs", "React/Vite foundation"],
  next: "Finish route verification and begin API v1 extraction."
};

export function normalizeProgress(value: number | undefined): number {
  if (typeof value !== "number" || Number.isNaN(value)) return 0;
  return Math.min(100, Math.max(0, Math.round(value)));
}
