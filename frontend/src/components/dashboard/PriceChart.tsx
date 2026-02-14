"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { fetchAPI } from "@/lib/api";
import type { HistoricalData } from "@/types";
import TradingViewChart, {
  type ChartType,
  type Indicator,
} from "@/components/charts/TradingViewChart";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useLanguageStore from "@/stores/useLanguageStore";
import { Search, Maximize2, Minimize2 } from "lucide-react";

/* ── Period config ──
   value     = display period (used as key / reference)
   fetch     = initial API period to request (bigger than value for scroll buffer)
   interval  = bar granularity
   visible   = how many bars to show initially (≈ the "value" window)
*/
const PERIODS = [
  { value: "1d",  fetch: "1mo",  label: "1D", interval: "5m",  visible: 78  },
  { value: "5d",  fetch: "1mo",  label: "5D", interval: "15m", visible: 130 },
  { value: "1mo", fetch: "1y",   label: "1M", interval: "1d",  visible: 22  },
  { value: "3mo", fetch: "2y",   label: "3M", interval: "1d",  visible: 65  },
  { value: "6mo", fetch: "5y",   label: "6M", interval: "1d",  visible: 130 },
  { value: "1y",  fetch: "5y",   label: "1Y", interval: "1d",  visible: 252 },
  { value: "5y",  fetch: "max",  label: "5Y", interval: "1wk", visible: 260 },
] as const;

/* Escalation ladder: when user scrolls to the edge we fetch a bigger period */
const FETCH_LADDER = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"] as const;

const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: "candlestick", label: "Candle" },
  { value: "line", label: "Line" },
  { value: "area", label: "Area" },
  { value: "heikin-ashi", label: "HA" },
];

const DEFAULT_INDICATORS: Indicator[] = [
  { id: "sma20", label: "SMA 20", enabled: false },
  { id: "sma50", label: "SMA 50", enabled: false },
  { id: "ema12", label: "EMA 12", enabled: false },
  { id: "ema26", label: "EMA 26", enabled: false },
  { id: "bb", label: "Bollinger", enabled: false },
];

const QUICK_PICKS = [
  { symbol: "SPY", label: "SPY" },
  { symbol: "QQQ", label: "QQQ" },
  { symbol: "AAPL", label: "AAPL" },
  { symbol: "TSLA", label: "TSLA" },
  { symbol: "BTC-USD", label: "BTC" },
  { symbol: "ETH-USD", label: "ETH" },
];

const DEFAULT_SYMBOL = "SPY";

export default function PriceChart() {
  const [symbol, setSymbol] = useState("");
  const [activeSymbol, setActiveSymbol] = useState("");
  const [periodIdx, setPeriodIdx] = useState(2); // 1M default
  const [data, setData] = useState<HistoricalData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<ChartType>("candlestick");
  const [indicators, setIndicators] = useState<Indicator[]>(DEFAULT_INDICATORS);
  const [fullscreen, setFullscreen] = useState(false);
  const { formatPrice } = useCurrencyStore();
  const t = useLanguageStore((s) => s.t);
  const didMount = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Track current fetch level for dynamic loading
  const currentFetchRef = useRef<string>("");
  const loadingMoreRef = useRef(false);

  const activePeriod = PERIODS[periodIdx];

  const fetchHistory = async (
    sym: string,
    interval: string,
    fetchPeriod: string,
    isLoadMore = false,
  ) => {
    const target = sym.trim().toUpperCase();
    if (!target) return;
    if (!isLoadMore) {
      setLoading(true);
      setError(null);
    }
    try {
      const result = await fetchAPI<HistoricalData>(
        `/api/v1/market/history/${target}?period=${fetchPeriod}&interval=${interval}`,
      );
      currentFetchRef.current = fetchPeriod;
      setData(result);
      setActiveSymbol(target);
    } catch (e) {
      if (!isLoadMore) {
        setError(e instanceof Error ? e.message : "Failed to load chart");
        setData(null);
      }
    } finally {
      if (!isLoadMore) setLoading(false);
      loadingMoreRef.current = false;
    }
  };

  const handleSearch = () =>
    fetchHistory(symbol, activePeriod.interval, activePeriod.fetch);

  const handlePeriodChange = (idx: number) => {
    setPeriodIdx(idx);
    const p = PERIODS[idx];
    if (activeSymbol) fetchHistory(activeSymbol, p.interval, p.fetch);
  };

  /** Called by the chart when the user scrolls near the left edge */
  const handleLoadMore = useCallback(() => {
    if (loadingMoreRef.current || !activeSymbol) return;
    const cur = currentFetchRef.current;
    const ladderIdx = FETCH_LADDER.indexOf(cur as any);
    if (ladderIdx < 0 || ladderIdx >= FETCH_LADDER.length - 1) return; // already at max
    const next = FETCH_LADDER[ladderIdx + 1];
    loadingMoreRef.current = true;
    fetchHistory(activeSymbol, activePeriod.interval, next, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSymbol, activePeriod.interval]);

  const toggleIndicator = (id: string) => {
    setIndicators((prev) =>
      prev.map((ind) => (ind.id === id ? { ...ind, enabled: !ind.enabled } : ind)),
    );
  };

  const toggleFullscreen = () => {
    if (!fullscreen) {
      containerRef.current?.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
    setFullscreen(!fullscreen);
  };

  useEffect(() => {
    if (!didMount.current) {
      didMount.current = true;
      fetchHistory(DEFAULT_SYMBOL, activePeriod.interval, activePeriod.fetch);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const onFs = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
  }, []);

  const chartData =
    data?.data.map((d) => ({
      date: d.date,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
      volume: d.volume,
    })) ?? [];

  const priceChange =
    chartData.length >= 2
      ? chartData[chartData.length - 1].close - chartData[0].close
      : 0;
  const isPositive = priceChange >= 0;

  return (
    <div
      ref={containerRef}
      className={`bg-oracle-panel border border-oracle-border rounded-lg p-4 ${
        fullscreen ? "fixed inset-0 z-50 rounded-none" : ""
      }`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          {t("chart.title")}
        </h3>
        <div className="flex items-center gap-1">
          {/* Chart type toggle */}
          {CHART_TYPES.map((ct) => (
            <button
              key={ct.value}
              onClick={() => setChartType(ct.value)}
              className={`text-[10px] px-1.5 py-0.5 rounded transition-colors ${
                chartType === ct.value
                  ? "bg-oracle-accent text-white"
                  : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
              }`}
            >
              {ct.label}
            </button>
          ))}
          <button
            onClick={toggleFullscreen}
            className="ml-1 p-1 text-oracle-muted hover:text-oracle-text transition-colors"
            title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-2 mb-2">
        <SymbolAutocomplete
          value={symbol}
          onChange={setSymbol}
          onSubmit={(s) => {
            setSymbol(s);
            fetchHistory(s, activePeriod.interval, activePeriod.fetch);
          }}
          placeholder={t("chart.placeholder")}
          className="flex-1"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !symbol.trim()}
          className="bg-oracle-accent text-white text-sm px-4 py-1.5 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "..." : t("chart.load")}
        </button>
      </div>

      {/* Quick picks + periods + indicators */}
      <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
        <div className="flex items-center gap-1.5 flex-wrap">
          <Search className="w-3 h-3 text-oracle-muted shrink-0" />
          {QUICK_PICKS.map((pick) => (
            <button
              key={pick.symbol}
              onClick={() => {
                setSymbol(pick.symbol);
                fetchHistory(pick.symbol, activePeriod.interval, activePeriod.fetch);
              }}
              className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                activeSymbol === pick.symbol
                  ? "bg-oracle-accent/20 text-oracle-accent border-oracle-accent/40"
                  : "bg-oracle-bg text-oracle-muted border-oracle-border hover:text-oracle-text hover:border-oracle-accent/30"
              }`}
            >
              {pick.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1 shrink-0">
          {PERIODS.map((p, i) => (
            <button
              key={p.value}
              onClick={() => handlePeriodChange(i)}
              className={`text-xs px-2 py-0.5 rounded transition-colors ${
                periodIdx === i
                  ? "bg-oracle-accent text-white"
                  : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Indicator toggles */}
      <div className="flex items-center gap-1 mb-2 flex-wrap">
        <span className="text-oracle-muted text-[10px] uppercase tracking-wide mr-1">Indicators</span>
        {indicators.map((ind) => (
          <button
            key={ind.id}
            onClick={() => toggleIndicator(ind.id)}
            className={`text-[10px] px-1.5 py-0.5 rounded border transition-colors ${
              ind.enabled
                ? "bg-oracle-accent/20 text-oracle-accent border-oracle-accent/40"
                : "bg-oracle-bg text-oracle-muted border-oracle-border hover:text-oracle-text"
            }`}
          >
            {ind.label}
          </button>
        ))}
      </div>

      {error && <p className="text-oracle-red text-sm mb-2">{error}</p>}

      {/* Loading skeleton */}
      {loading && !data && (
        <div className="animate-pulse">
          <div className="flex items-baseline gap-2 mb-2">
            <div className="h-5 w-12 bg-oracle-bg rounded" />
            <div className="h-6 w-24 bg-oracle-bg rounded" />
          </div>
          <div className="h-64 bg-oracle-bg rounded" />
        </div>
      )}

      {data && chartData.length > 0 && (
        <div>
          {/* Price header */}
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-oracle-text font-bold">{activeSymbol}</span>
            <span className="text-oracle-text text-lg font-mono">
              {formatPrice(chartData[chartData.length - 1].close)}
            </span>
            <span
              className={`text-sm ${isPositive ? "text-oracle-green" : "text-oracle-red"}`}
            >
              {isPositive ? "+" : ""}
              {formatPrice(priceChange)}
            </span>
          </div>

          {/* Chart */}
          <div className={fullscreen ? "h-[calc(100vh-220px)]" : "h-80"}>
            <TradingViewChart
              data={chartData}
              chartType={chartType}
              indicators={indicators}
              fullscreen={fullscreen}
              formatPrice={(v) => formatPrice(v)}
              visibleBars={activePeriod.visible}
              onLoadMore={handleLoadMore}
            />
          </div>
        </div>
      )}
    </div>
  );
}
