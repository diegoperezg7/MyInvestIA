"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  AreaSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type SeriesType,
  type Time,
  ColorType,
  CrosshairMode,
} from "lightweight-charts";

export type ChartType = "candlestick" | "line" | "area" | "heikin-ashi";

export interface Indicator {
  id: string;
  label: string;
  enabled: boolean;
}

interface OHLCVData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Props {
  data: OHLCVData[];
  chartType?: ChartType;
  indicators?: Indicator[];
  fullscreen?: boolean;
  formatPrice?: (v: number) => string;
}

function toHeikinAshi(data: OHLCVData[]): OHLCVData[] {
  const result: OHLCVData[] = [];
  for (let i = 0; i < data.length; i++) {
    const d = data[i];
    const haClose = (d.open + d.high + d.low + d.close) / 4;
    const haOpen =
      i === 0
        ? (d.open + d.close) / 2
        : (result[i - 1].open + result[i - 1].close) / 2;
    const haHigh = Math.max(d.high, haOpen, haClose);
    const haLow = Math.min(d.low, haOpen, haClose);
    result.push({ ...d, open: haOpen, high: haHigh, low: haLow, close: haClose });
  }
  return result;
}

function computeSMA(closes: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += closes[j];
      result.push(sum / period);
    }
  }
  return result;
}

function computeEMA(closes: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  const k = 2 / (period + 1);
  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else if (i === period - 1) {
      let sum = 0;
      for (let j = 0; j < period; j++) sum += closes[j];
      result.push(sum / period);
    } else {
      const prev = result[i - 1]!;
      result.push(closes[i] * k + prev * (1 - k));
    }
  }
  return result;
}

function computeBollingerBands(
  closes: number[],
  period = 20,
  stdDev = 2
): { upper: (number | null)[]; middle: (number | null)[]; lower: (number | null)[] } {
  const middle = computeSMA(closes, period);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (middle[i] === null) {
      upper.push(null);
      lower.push(null);
    } else {
      let variance = 0;
      for (let j = i - period + 1; j <= i; j++) {
        variance += (closes[j] - middle[i]!) ** 2;
      }
      const std = Math.sqrt(variance / period);
      upper.push(middle[i]! + stdDev * std);
      lower.push(middle[i]! - stdDev * std);
    }
  }
  return { upper, middle, lower };
}

export default function TradingViewChart({
  data,
  chartType = "candlestick",
  indicators = [],
  fullscreen = false,
  formatPrice,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainSeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const [tooltipData, setTooltipData] = useState<{
    time: string; open: number; high: number; low: number; close: number; volume: number;
  } | null>(null);

  const isIndicatorEnabled = useCallback(
    (id: string) => indicators.find((ind) => ind.id === id)?.enabled ?? false,
    [indicators]
  );

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    // Cleanup previous chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      mainSeriesRef.current = null;
      volumeSeriesRef.current = null;
    }

    const container = containerRef.current;
    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue("--oracle-text").trim() || "#e2e8f0";
    const borderColor = styles.getPropertyValue("--oracle-border").trim() || "#1e293b";

    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: textColor,
        fontSize: 11,
      },
      grid: {
        vertLines: { color: borderColor, style: 1 },
        horzLines: { color: borderColor, style: 1 },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: borderColor,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
      timeScale: {
        borderColor: borderColor,
        timeVisible: false,
        rightOffset: 5,
        minBarSpacing: 3,
      },
    });
    chartRef.current = chart;

    // Normalize date to yyyy-mm-dd (lightweight-charts v5 requirement)
    const toDay = (dateStr: string): Time =>
      dateStr.slice(0, 10) as Time; // "2026-01-14T00:00:00-05:00" → "2026-01-14"

    // Prepare data — deduplicate by date (keep last entry per date, required by lightweight-charts)
    const rawData = chartType === "heikin-ashi" ? toHeikinAshi(data) : data;
    const dateMap = new Map<string, OHLCVData>();
    for (const d of rawData) {
      dateMap.set(d.date.slice(0, 10), d);
    }
    const displayData = Array.from(dateMap.values()).sort(
      (a, b) => a.date.localeCompare(b.date)
    );
    const times = displayData.map((d) => toDay(d.date));
    const closes = displayData.map((d) => d.close);

    // Determine trend color: green if bullish, red if bearish
    const firstClose = displayData[0]?.close ?? 0;
    const lastClose = displayData[displayData.length - 1]?.close ?? 0;
    const isBullish = lastClose >= firstClose;
    const trendColor = isBullish ? "#10b981" : "#ef4444";

    // Main series
    if (chartType === "line") {
      const series = chart.addSeries(LineSeries, {
        color: trendColor,
        lineWidth: 2,
      });
      series.setData(
        displayData.map((d) => ({ time: toDay(d.date), value: d.close }))
      );
      mainSeriesRef.current = series;
    } else if (chartType === "area") {
      const series = chart.addSeries(AreaSeries, {
        topColor: isBullish ? "rgba(16, 185, 129, 0.4)" : "rgba(239, 68, 68, 0.4)",
        bottomColor: isBullish ? "rgba(16, 185, 129, 0.0)" : "rgba(239, 68, 68, 0.0)",
        lineColor: trendColor,
        lineWidth: 2,
      });
      series.setData(
        displayData.map((d) => ({ time: toDay(d.date), value: d.close }))
      );
      mainSeriesRef.current = series;
    } else {
      // Candlestick or Heikin Ashi
      const series = chart.addSeries(CandlestickSeries, {
        upColor: "#10b981",
        downColor: "#ef4444",
        borderDownColor: "#ef4444",
        borderUpColor: "#10b981",
        wickDownColor: "#ef4444",
        wickUpColor: "#10b981",
      });
      series.setData(
        displayData.map((d) => ({
          time: toDay(d.date),
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }))
      );
      mainSeriesRef.current = series;
    }

    // Volume histogram
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: trendColor,
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    volumeSeries.setData(
      displayData.map((d) => ({
        time: toDay(d.date),
        value: d.volume,
        color: d.close >= d.open ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)",
      }))
    );
    volumeSeriesRef.current = volumeSeries;

    // Indicator overlays
    const addLineSeries = (
      lineData: (number | null)[],
      color: string,
      title: string,
      lineWidth: number = 1,
      lineStyle?: number
    ) => {
      const opts: Record<string, unknown> = { color, lineWidth, title };
      if (lineStyle !== undefined) opts.lineStyle = lineStyle;
      const series = chart.addSeries(LineSeries, opts as any);
      series.setData(
        lineData
          .map((v, i) => (v !== null ? { time: times[i], value: v } : null))
          .filter(Boolean) as { time: Time; value: number }[]
      );
    };

    if (isIndicatorEnabled("sma20")) addLineSeries(computeSMA(closes, 20), "#f59e0b", "SMA 20");
    if (isIndicatorEnabled("sma50")) addLineSeries(computeSMA(closes, 50), "#3b82f6", "SMA 50");
    if (isIndicatorEnabled("ema12")) addLineSeries(computeEMA(closes, 12), "#ec4899", "EMA 12");
    if (isIndicatorEnabled("ema26")) addLineSeries(computeEMA(closes, 26), "#14b8a6", "EMA 26");

    if (isIndicatorEnabled("bb")) {
      const bb = computeBollingerBands(closes, 20, 2);
      addLineSeries(bb.upper, "rgba(148, 163, 184, 0.5)", "BB Upper");
      addLineSeries(bb.middle, "rgba(148, 163, 184, 0.3)", "BB Mid", 1, 2);
      addLineSeries(bb.lower, "rgba(148, 163, 184, 0.5)", "BB Lower");
    }

    // Crosshair tooltip
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData || !mainSeriesRef.current) {
        setTooltipData(null);
        return;
      }
      const mainData = param.seriesData.get(mainSeriesRef.current) as Record<string, unknown> | undefined;
      if (!mainData) {
        setTooltipData(null);
        return;
      }
      const volData = volumeSeriesRef.current
        ? (param.seriesData.get(volumeSeriesRef.current) as Record<string, unknown> | undefined)
        : undefined;
      setTooltipData({
        time: String(param.time),
        open: Number(mainData.open ?? mainData.value ?? 0),
        high: Number(mainData.high ?? mainData.value ?? 0),
        low: Number(mainData.low ?? mainData.value ?? 0),
        close: Number(mainData.close ?? mainData.value ?? 0),
        volume: Number(volData?.value ?? 0),
      });
    });

    chart.timeScale().fitContent();

    // ResizeObserver
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data, chartType, isIndicatorEnabled]);

  const fmt = formatPrice || ((v: number) => v.toFixed(2));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-oracle-muted text-sm">
        No chart data
      </div>
    );
  }

  return (
    <div className={`relative w-full ${fullscreen ? "h-screen" : "h-full"}`}>
      <div ref={containerRef} className="w-full h-full" />
      {tooltipData && (
        <div className="absolute top-2 left-2 bg-oracle-panel/90 border border-oracle-border rounded px-2 py-1.5 text-xs pointer-events-none z-10 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <span className="text-oracle-muted">{tooltipData.time}</span>
            <span className="text-oracle-muted">O</span>
            <span className="text-oracle-text font-mono">{fmt(tooltipData.open)}</span>
            <span className="text-oracle-muted">H</span>
            <span className="text-oracle-text font-mono">{fmt(tooltipData.high)}</span>
            <span className="text-oracle-muted">L</span>
            <span className="text-oracle-text font-mono">{fmt(tooltipData.low)}</span>
            <span className="text-oracle-muted">C</span>
            <span className={`font-mono ${tooltipData.close >= tooltipData.open ? "text-oracle-green" : "text-oracle-red"}`}>
              {fmt(tooltipData.close)}
            </span>
            <span className="text-oracle-muted">Vol</span>
            <span className="text-oracle-text font-mono">
              {tooltipData.volume >= 1e6
                ? `${(tooltipData.volume / 1e6).toFixed(1)}M`
                : tooltipData.volume >= 1e3
                ? `${(tooltipData.volume / 1e3).toFixed(1)}K`
                : tooltipData.volume.toLocaleString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
