"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import { fetchAPI } from "@/lib/api";
import type { HistoricalData } from "@/types";

const PERIODS = ["1mo", "3mo", "6mo", "1y"] as const;

export default function PriceChart() {
  const [symbol, setSymbol] = useState("");
  const [activeSymbol, setActiveSymbol] = useState("");
  const [period, setPeriod] = useState<string>("1mo");
  const [data, setData] = useState<HistoricalData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async (sym: string, per: string) => {
    if (!sym.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAPI<HistoricalData>(
        `/api/v1/market/history/${sym.trim().toUpperCase()}?period=${per}&interval=1d`
      );
      setData(result);
      setActiveSymbol(sym.trim().toUpperCase());
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

  const chartData =
    data?.data.map((d) => ({
      date: new Date(d.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
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
      <h3 className="text-oracle-muted text-sm font-medium mb-3 uppercase tracking-wide">
        Price Chart
      </h3>

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Symbol (e.g. AAPL)"
          className="flex-1 bg-oracle-bg border border-oracle-border rounded px-3 py-1.5 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !symbol.trim()}
          className="bg-oracle-accent text-white text-sm px-4 py-1.5 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "..." : "Load"}
        </button>
      </div>

      {activeSymbol && (
        <div className="flex gap-1 mb-3">
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
      )}

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {data && chartData.length > 0 && (
        <div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-white font-bold">{activeSymbol}</span>
            <span className="text-white text-lg font-mono">
              ${chartData[chartData.length - 1].close.toFixed(2)}
            </span>
            <span
              className={`text-sm ${
                isPositive ? "text-oracle-green" : "text-oracle-red"
              }`}
            >
              {isPositive ? "+" : ""}
              {priceChange.toFixed(2)}
            </span>
          </div>

          <div className="h-48">
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
                  dataKey="date"
                  tick={{ fill: "#6b7280", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  domain={["auto", "auto"]}
                  tick={{ fill: "#6b7280", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={60}
                  tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#111827",
                    border: "1px solid #1f2937",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "#e5e7eb",
                  }}
                  formatter={(value: number) => [
                    `$${value.toFixed(2)}`,
                    "Price",
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
          </div>
        </div>
      )}

      {!data && !loading && !error && (
        <p className="text-oracle-muted text-sm">
          Enter a symbol to view price history.
        </p>
      )}
    </div>
  );
}
