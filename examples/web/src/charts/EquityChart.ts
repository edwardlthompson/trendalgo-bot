import { createChart, type IChartApi, type ISeriesApi, type LineData } from "lightweight-charts";
import { chartThemeFromTokens } from "../design-system/chartTheme";

export type EquityPoint = { time: number; value: number };

export function renderEquityChart(
  container: HTMLElement,
  points: EquityPoint[],
): () => void {
  const theme = chartThemeFromTokens();
  const chart: IChartApi = createChart(container, {
    width: container.clientWidth,
    height: 220,
    layout: { background: { color: theme.background }, textColor: theme.text },
    grid: {
      vertLines: { color: theme.grid },
      horzLines: { color: theme.grid },
    },
  });
  const series: ISeriesApi<"Line"> = chart.addLineSeries({ color: theme.line, lineWidth: 2 });
  const data: LineData[] = points.map((p) => ({ time: p.time as LineData["time"], value: p.value }));
  if (data.length) series.setData(data);
  chart.timeScale().fitContent();

  const onResize = (): void => {
    chart.applyOptions({ width: container.clientWidth });
  };
  window.addEventListener("resize", onResize);
  return () => {
    window.removeEventListener("resize", onResize);
    chart.remove();
  };
}
