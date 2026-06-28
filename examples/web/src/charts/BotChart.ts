import {
  createChart,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type SeriesMarker,
  type UTCTimestamp,
} from "lightweight-charts";
import { chartThemeFromTokens } from "../design-system/chartTheme";
import type { EquityPoint } from "./EquityChart";

export type BotTradeMarker = {
  time: number;
  side: string;
  pnl_usd?: number;
  pnl_pct?: number;
};

export type OhlcvCandle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

export type TradeHighlightRegion = {
  time_start: number;
  time_end: number;
  entry_price: number;
  exit_price: number;
  profitable: boolean;
  pnl_usd?: number | null;
};

export type BotChartData = {
  points: EquityPoint[];
  ohlcv?: OhlcvCandle[];
  trades: BotTradeMarker[];
  regions?: TradeHighlightRegion[];
};

function formatMarkerText(trade: BotTradeMarker): string {
  const buy = trade.side.toLowerCase() === "buy";
  if (buy) return "▲";
  const pnl = trade.pnl_usd;
  if (pnl == null) return "▼";
  const sign = pnl >= 0 ? "+" : "-";
  const abs = Math.abs(pnl);
  const pct = trade.pnl_pct;
  const pctPart = pct != null ? ` (${sign}${Math.abs(pct).toFixed(2)}%)` : "";
  return `▼ ${sign}$${abs.toFixed(2)}${pctPart}`;
}

function toLineData(points: EquityPoint[]): LineData[] {
  return points.map((p) => ({
    time: p.time as UTCTimestamp,
    value: p.value,
  }));
}

function toCandles(candles: OhlcvCandle[]): CandlestickData[] {
  return candles.map((c) => ({
    time: c.time as UTCTimestamp,
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }));
}

function toMarkers(trades: BotTradeMarker[]): SeriesMarker<UTCTimestamp>[] {
  const theme = chartThemeFromTokens();
  return trades.map((trade) => {
    const buy = trade.side.toLowerCase() === "buy";
    return {
      time: trade.time as UTCTimestamp,
      position: buy ? "belowBar" : "aboveBar",
      color: buy ? theme.profit : theme.loss,
      shape: buy ? "arrowUp" : "arrowDown",
      text: formatMarkerText(trade),
    };
  });
}

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

export function renderBotChart(
  container: HTMLElement,
  data: BotChartData,
): {
  cleanup: () => void;
  setData: (next: BotChartData) => void;
} {
  const theme = chartThemeFromTokens();
  let cancelled = false;
  let pending = data;
  let chart: IChartApi | null = null;
  let useCandles = Boolean(data.ohlcv?.length);
  let priceSeries: ISeriesApi<"Candlestick"> | ISeriesApi<"Line"> | null = null;
  const regionSeries: ISeriesApi<"Baseline">[] = [];
  let ro: ResizeObserver | null = null;

  const fitContent = (): void => {
    chart?.timeScale().fitContent();
  };

  const clearRegions = (): void => {
    for (const series of regionSeries.splice(0)) {
      chart?.removeSeries(series);
    }
  };

  const addRegions = (regions: TradeHighlightRegion[], candles: OhlcvCandle[]): void => {
    if (!chart || !regions.length || !candles.length) return;
    const byTime = new Map(candles.map((c) => [c.time, c]));
    const times = candles.map((c) => c.time).sort((a, b) => a - b);
    const closeAt = (ts: number): number => {
      const hit = byTime.get(ts);
      if (hit) return hit.close;
      const prior = times.filter((t) => t <= ts);
      const key = prior.length ? prior[prior.length - 1]! : times[0]!;
      return byTime.get(key)?.close ?? 0;
    };
    for (const region of regions) {
      const entry = region.entry_price || closeAt(region.time_start);
      const profitable = region.profitable;
      const fill = profitable ? "rgba(38, 166, 154, 0.22)" : "rgba(239, 83, 80, 0.22)";
      const top = profitable ? "rgba(38, 166, 154, 0.35)" : "rgba(239, 83, 80, 0.35)";
      const baseline = chart.addBaselineSeries({
        baseValue: { type: "price", price: entry },
        topFillColor1: top,
        topFillColor2: top,
        bottomFillColor1: fill,
        bottomFillColor2: fill,
        topLineColor: "transparent",
        bottomLineColor: "transparent",
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const segment = candles.filter((c) => c.time >= region.time_start && c.time <= region.time_end);
      const lineData = (segment.length ? segment : candles).map((c) => ({
        time: c.time as UTCTimestamp,
        value: c.close,
      }));
      if (lineData.length) baseline.setData(lineData);
      regionSeries.push(baseline);
    }
  };

  const applyData = (next: BotChartData): void => {
    pending = next;
    if (!priceSeries || !chart) return;
    clearRegions();
    const candles = next.ohlcv?.length ? next.ohlcv : undefined;
    useCandles = Boolean(candles?.length);
    if (useCandles && candles) {
      (priceSeries as ISeriesApi<"Candlestick">).setData(toCandles(candles));
    } else if (next.points.length) {
      (priceSeries as ISeriesApi<"Line">).setData(toLineData(next.points));
    }
    priceSeries.setMarkers(toMarkers(next.trades));
    addRegions(next.regions ?? [], candles ?? next.points.map((p) => ({
      time: p.time,
      open: p.value,
      high: p.value,
      low: p.value,
      close: p.value,
    })));
    fitContent();
  };

  const cancelReady = whenContainerReady(container, () => {
    if (cancelled) return;
    chart = createChart(container, {
      autoSize: true,
      height: 320,
      layout: { background: { color: theme.background }, textColor: theme.text },
      grid: {
        vertLines: { color: theme.grid },
        horzLines: { color: theme.grid },
      },
      timeScale: { fixLeftEdge: true, fixRightEdge: true },
    });
    useCandles = Boolean(pending.ohlcv?.length);
    priceSeries = useCandles
      ? chart.addCandlestickSeries({
          upColor: theme.profit,
          downColor: theme.loss,
          borderVisible: false,
          wickUpColor: theme.profit,
          wickDownColor: theme.loss,
        })
      : chart.addLineSeries({ color: theme.line, lineWidth: 2 });
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
