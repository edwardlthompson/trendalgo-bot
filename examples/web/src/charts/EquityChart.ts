import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
} from "lightweight-charts";
import { chartThemeFromTokens } from "../design-system/chartTheme";

export type EquityPoint = { time: number; value: number };

export type PerformanceComparison = {
  portfolio_return_pct: number;
  top10_return_pct: number;
  alpha_pct: number;
};

function toLineData(points: EquityPoint[]): LineData[] {
  return points.map((p) => ({
    time: p.time as UTCTimestamp,
    value: p.value,
  }));
}

function baseChartOptions(height: number) {
  const theme = chartThemeFromTokens();
  return {
    autoSize: true,
    height,
    layout: { background: { color: theme.background }, textColor: theme.text },
    grid: {
      vertLines: { color: theme.grid },
      horzLines: { color: theme.grid },
    },
    timeScale: {
      fixLeftEdge: true,
      fixRightEdge: true,
    },
  } as const;
}

/** Wait until the host is connected and laid out (avoids 280px fallback width). */
function whenContainerReady(container: HTMLElement, cb: () => void): () => void {
  let cancelled = false;
  const run = (): void => {
    if (cancelled) return;
    if (container.isConnected && container.clientWidth > 0) {
      cb();
      return;
    }
    requestAnimationFrame(run);
  };
  run();
  return () => {
    cancelled = true;
  };
}

export function renderEquityChart(
  container: HTMLElement,
  points: EquityPoint[],
): { cleanup: () => void; setData: (next: EquityPoint[]) => void } {
  const theme = chartThemeFromTokens();
  let cancelled = false;
  let pending = points;
  let chart: IChartApi | null = null;
  let series: ISeriesApi<"Line"> | null = null;
  let ro: ResizeObserver | null = null;

  const fitContent = (): void => {
    chart?.timeScale().fitContent();
  };

  const applyData = (next: EquityPoint[]): void => {
    pending = next;
    if (!series) return;
    if (next.length) {
      series.setData(toLineData(next));
      fitContent();
    }
  };

  const cancelReady = whenContainerReady(container, () => {
    if (cancelled) return;
    chart = createChart(container, baseChartOptions(260));
    series = chart.addLineSeries({ color: theme.line, lineWidth: 2 });
    applyData(pending);
    ro = new ResizeObserver(() => fitContent());
    ro.observe(container);
  });

  return {
    setData: applyData,
    cleanup: () => {
      cancelled = true;
      cancelReady();
      ro?.disconnect();
      chart?.remove();
    },
  };
}

export function renderPerformanceComparisonChart(
  container: HTMLElement,
  portfolio: EquityPoint[],
  benchmark: EquityPoint[],
): { cleanup: () => void; setData: (p: EquityPoint[], b: EquityPoint[]) => void } {
  const theme = chartThemeFromTokens();
  let cancelled = false;
  let pendingPortfolio = portfolio;
  let pendingBenchmark = benchmark;
  let chart: IChartApi | null = null;
  let portfolioSeries: ISeriesApi<"Line"> | null = null;
  let benchmarkSeries: ISeriesApi<"Line"> | null = null;
  let ro: ResizeObserver | null = null;

  const fitContent = (): void => {
    chart?.timeScale().fitContent();
  };

  const applyData = (p: EquityPoint[], b: EquityPoint[]): void => {
    pendingPortfolio = p;
    pendingBenchmark = b;
    if (!chart) return;
    if (p.length) {
      portfolioSeries!.setData(toLineData(p));
    }
    if (b.length) {
      benchmarkSeries!.setData(toLineData(b));
    }
    if (p.length || b.length) {
      fitContent();
    }
  };

  const cancelReady = whenContainerReady(container, () => {
    if (cancelled) return;
    chart = createChart(container, baseChartOptions(280));
    portfolioSeries = chart.addLineSeries({
      color: theme.line,
      lineWidth: 2,
      title: "Portfolio",
    });
    benchmarkSeries = chart.addLineSeries({
      color: theme.secondary ?? theme.profit,
      lineWidth: 2,
      lineStyle: 2,
      title: "Top 10",
    });
    applyData(pendingPortfolio, pendingBenchmark);
    ro = new ResizeObserver(() => fitContent());
    ro.observe(container);
  });

  return {
    setData: applyData,
    cleanup: () => {
      cancelled = true;
      cancelReady();
      ro?.disconnect();
      chart?.remove();
    },
  };
}
