import type { RunArtifact, StructuredChartData, StructuredChartPoint } from "../types";
import { ArtifactCard } from "./ArtifactViewer";

const palette = ["#b8653b", "#5f7f67", "#315f72", "#b28a3f", "#8a5a7d", "#64748b"];

function chartKind(chart: StructuredChartData) {
  return String(chart.kind || chart.chart_type || chart.type || "summary").toLowerCase();
}

function titleForChart(chart: StructuredChartData) {
  return chart.title || chart.name || chart.chart_id || chart.id || "Chart";
}

function toNumber(value: unknown) {
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) ? number : 0;
}

function labelOf(point: StructuredChartPoint, fallback: string) {
  return String(point.label || point.name || point.category || fallback);
}

function valueOf(point: StructuredChartPoint) {
  return toNumber(point.value ?? point.score ?? point.count ?? point.percent);
}

function pointsFrom(chart: StructuredChartData): Array<{ label: string; value: numbe        r }> {
  if (Array.isArray(chart.points)) {
    return chart.points.map((point, index) => ({ label: labelOf(point, `Item ${index + 1}`), value: valueOf(point) }));
  }

  if (Array.isArray(chart.data)) {
    return chart.data.map((point, index) => ({ label: labelOf(point, `Item ${index + 1}`), value: valueOf(point) }));
  }

  if (chart.labels?.length || chart.values?.length) {
    return (chart.labels ?? chart.values?.map((_, index) => `Item ${index + 1}`) ?? []).map((label, index) => ({
      label,
      value: toNumber(chart.values?.[index])
    }));
  }

  const seriesPoints = chart.series?.flatMap((series) => {
    if (Array.isArray(series.points)) return series.points;
    if (Array.isArray(series.data) && typeof series.data[0] === "object") return series.data as StructuredChartPoint[];
    if (Array.isArray(series.values)) {
      return series.values.map((value, index) => ({ label: `${series.name || series.label || "Series"} ${index + 1}`, value }));
    }
    if (series.value !== undefined) return [{ label: series.name || series.label || "Series", value: series.value }];
    return [];
  });

  if (seriesPoints?.length) {
    return seriesPoints.map((point, index) => ({ label: labelOf(point, `Item ${index + 1}`), value: valueOf(point) }));
  }

  if (chart.metrics) {
    return Object.entries(chart.metrics).map(([label, value]) => ({ label, value: toNumber(value) }));
  }

  if (chart.data && !Array.isArray(chart.data)) {
    return Object.entries(chart.data).map(([label, value]) => ({ label, value: toNumber(value) }));
  }

  return [];
}

function DonutChart({ points }: { points: Array<{ label: string; value: number }> }) {
  const total = points.reduce((sum, point) => sum + Math.max(0, point.value), 0);
  let cursor = 0;
  const gradient =
    total > 0
      ? points
          .map((point, index) => {
            const start = cursor;
            cursor += (Math.max(0, point.value) / total) * 100;
            return `${palette[index % palette.length]} ${start}% ${cursor}%`;
          })
          .join(", ")
      : `${palette[5]} 0 100%`;

  return (
    <div className="native-donut">
      <div className="donut-ring" style={{ background: `conic-gradient(${gradient})` }}>
        <strong>{total.toLocaleString()}</strong>
        <span>Total</span>
      </div>
      <ChartLegend points={points} total={total} />
    </div>
  );
}

function BarChart({ points, lollipop = false }: { points: Array<{ label: string; value: number }>; lollipop?: boolean }) {
  const max = Math.max(...points.map((point) => Math.abs(point.value)), 1);
  return (
    <div className={lollipop ? "native-bars lollipop" : "native-bars"}>
      {points.map((point, index) => (
        <div className="native-bar-row" key={`${point.label}-${index}`}>
          <span>{point.label}</span>
          <div className="native-bar-track">
            <i style={{ width: `${Math.max(3, (Math.abs(point.value) / max) * 100)}%`, background: palette[index % palette.length] }} />
          </div>
          <strong>{point.value.toLocaleString()}</strong>
        </div>
      ))}
    </div>
  );
}

function RadarChart({ points }: { points: Array<{ label: string; value: number }> }) {
  const size = 220;
  const center = size / 2;
  const radius = 82;
  const max = Math.max(...points.map((point) => Math.abs(point.value)), 1);
  const polygon = points
    .map((point, index) => {
      const angle = (Math.PI * 2 * index) / points.length - Math.PI / 2;
      const distance = (Math.abs(point.value) / max) * radius;
      return `${center + Math.cos(angle) * distance},${center + Math.sin(angle) * distance}`;
    })
    .join(" ");

  return (
    <div className="native-radar">
      <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Radar summary">
        {[0.33, 0.66, 1].map((scale) => (
          <circle key={scale} cx={center} cy={center} r={radius * scale} />
        ))}
        {points.map((point, index) => {
          const angle = (Math.PI * 2 * index) / points.length - Math.PI / 2;
          return (
            <line
              key={`${point.label}-${index}`}
              x1={center}
              y1={center}
              x2={center + Math.cos(angle) * radius}
              y2={center + Math.sin(angle) * radius}
            />
          );
        })}
        <polygon points={polygon} />
      </svg>
      <ChartLegend points={points} total={max} />
    </div>
  );
}

function SummaryChart({ points }: { points: Array<{ label: string; value: number }> }) {
  return (
    <div className="native-summary">
      {points.map((point, index) => (
        <div key={`${point.label}-${index}`}>
          <span>{point.label}</span>
          <strong>{point.value.toLocaleString()}</strong>
        </div>
      ))}
    </div>
  );
}

function ChartLegend({ points, total }: { points: Array<{ label: string; value: number }>; total: number }) {
  return (
    <div className="chart-legend">
      {points.map((point, index) => (
        <div key={`${point.label}-${index}`}>
          <i style={{ background: palette[index % palette.length] }} />
          <span>{point.label}</span>
          <strong>{total > 0 ? `${Math.round((point.value / total) * 100)}%` : point.value.toLocaleString()}</strong>
        </div>
      ))}
    </div>
  );
}

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

export function StructuredChartCard({ chart }: { chart: StructuredChartData }) {
  const points = pointsFrom(chart).filter((point) => point.label && Number.isFinite(point.value)).slice(0, 10);
  const kind = chartKind(chart);
  const artifact: RunArtifact = {
    name: titleForChart(chart),
    title: titleForChart(chart),
    summary: chart.summary,
    status: chart.status || (points.length ? "ready" : "missing"),
    open_url: chart.open_url,
    download_url: chart.download_url
  };

  return (
    <ArtifactCard artifact={artifact}>
      {points.length ? (
        <div className="native-chart-card">
          {kind.includes("donut") || kind.includes("pie") ? <DonutChart points={points} /> : null}
          {kind.includes("bar") ? <BarChart points={points} /> : null}
          {kind.includes("lollipop") ? <BarChart points={points} lollipop /> : null}
          {kind.includes("radar") ? <RadarChart points={points} /> : null}
          {kind.includes("summary") || kind.includes("metric") || kind.includes("kpi") ? <SummaryChart points={points} /> : null}
          {!["donut", "pie", "bar", "lollipop", "radar", "summary", "metric", "kpi"].some((item) => kind.includes(item)) ? (
            <SummaryChart points={points} />
          ) : null}
        </div>
      ) : chart.open_url ? (
        <iframe className="chart-frame" src={chart.open_url} title={titleForChart(chart)} loading="lazy" />
      ) : (
        <div className="chart-placeholder">Structured chart data unavailable</div>
      )}
    </ArtifactCard>
  );
}
