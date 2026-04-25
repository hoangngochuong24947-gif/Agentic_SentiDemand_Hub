import type { RunArtifact } from "../types";
import { ArtifactCard } from "./ArtifactViewer";

export function ChartCard({ chart }: { chart: RunArtifact }) {
  return (
    <ArtifactCard artifact={chart}>
      {chart.status === "ready" && chart.open_url ? (
        <iframe className="chart-frame" src={chart.open_url} title={chart.title || chart.name} loading="lazy" />
      ) : (
        <div className="chart-placeholder">Missing</div>
      )}
    </ArtifactCard>
  );
}
