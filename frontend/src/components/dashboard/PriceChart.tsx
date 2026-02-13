"use client";

import { useState, useEffect, useRef } from "react";
import {
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import { fetchAPI } from "@/lib/api";
import type { HistoricalData } from "@/types";
import CandlestickChart from "@/components/charts/CandlestickChart";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useLanguageStore from "@/stores/useLanguageStore";
import { Search } from "lucide-react";

const PERIODS = ["1mo", "3mo", "6mo", "1y"] as const;
type ChartMode = "area" | "candlestick";

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
  const [period, setPeriod] = useState<string>("1mo");
  const [data, setData] = useState<HistoricalData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartMode, setChartMode] = useState<ChartMode>("area");
  const { formatPrice } = useCurrencyStore();
  const t = useLanguageStore((s) => s.t);
  const didMount = useRef(false);

  const fetchHistory = async (sym: string, per: string) => {
    const target = sym.trim().toUpperCase();
    if (!target) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAPI<HistoricalData>(
        `/api/v1/market/history/${target}?period=${per}&interval=1d`
      );
      setData(result);
      setActiveSymbol(target);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load chart");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => fetchHistory(symbol, period);

  const handlePeriodChange = (p: string) => {
    setPeriod(p);
    if (activeSymbol) fetchHistory(activeSymbol, p);
  };

  // Auto-load default chart on mount
  useEffect(() => {
    if (!didMount.current) {
      didMount.current = true;
      fetchHistory(DEFAULT_SYMBOL, period);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const chartData =
    data?.data.map((d) => ({
      date: d.date,
      displayDate: new Date(d.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
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
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          {t("chart.title")}
        </h3>
        <div className="flex gap-1">
          <button
            onClick={() => setChartMode("area")}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              chartMode === "area"
                ? "bg-oracle-accent text-white"
                : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
            }`}
          >
            {t("chart.area")}
          </button>
          <button
            onClick={() => setChartMode("candlestick")}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              chartMode === "candlestick"
                ? "bg-oracle-accent text-white"
                : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
            }`}
          >
            {t("chart.candle")}
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-3">
        <SymbolAutocomplete
          value={symbol}
          onChange={setSymbol}
          onSubmit={(s) => { setSymbol(s); fetchHistory(s, period); }}
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

      {/* Quick picks + period selector */}
      <div className="flex items-center justify-between mb-3 gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <Search className="w-3 h-3 text-oracle-muted shrink-0" />
          {QUICK_PICKS.map((pick) => (
            <button
              key={pick.symbol}
              onClick={() => { setSymbol(pick.symbol); fetchHistory(pick.symbol, period); }}
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
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => handlePeriodChange(p)}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                period === p
                  ? "bg-oracle-accent text-white"
                  : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
              }`}
            >
              {p.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {/* Loading skeleton */}
      {loading && !data && (
        <div className="animate-pulse">
          <div className="flex items-baseline gap-2 mb-2">
            <div className="h-5 w-12 bg-oracle-bg rounded" />
            <div className="h-6 w-24 bg-oracle-bg rounded" />
            <div className="h-4 w-16 bg-oracle-bg rounded" />
          </div>
          <div className="h-48 bg-oracle-bg rounded" />
        </div>
      )}

      {data && chartData.length > 0 && (
        <div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-oracle-text font-bold">{activeSymbol}</span>
            <span className="text-oracle-text text-lg font-mono">
              {formatPrice(chartData[chartData.length - 1].close)}
            </span>
            <span
              className={`text-sm ${
                isPositive ? "text-oracle-green" : "text-oracle-red"
              }`}
            >
              {isPositive ? "+" : ""}
              {formatPrice(priceChange)}
            </span>
          </div>

          <div className="h-48">
            {chartMode === "candlestick" ? (
              <CandlestickChart data={chartData} formatPrice={formatPrice} />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="5%"
                        stopColor={isPositive ? "#10b981" : "#ef4444"}
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="95%"
                        stopColor={isPositive ? "#10b981" : "#ef4444"}
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="displayDate"
                    tick={{ fill: "var(--oracle-muted)", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fill: "var(--oracle-muted)", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    width={60}
                    tickFormatter={(v: number) => formatPrice(v, 0)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--oracle-panel)",
                      border: "1px solid var(--oracle-border)",
                      borderRadius: "8px",
                      fontSize: "12px",
                      color: "var(--oracle-text)",
                    }}
                    formatter={(value: number) => [
                      formatPrice(value),
                      t("chart.price"),
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="close"
                    stroke={isPositive ? "#10b981" : "#ef4444"}
                    strokeWidth={2}
                    fill="url(#colorPrice)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
