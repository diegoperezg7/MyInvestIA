"use client";

import { useState, useEffect } from "react";
import { fetchAPI } from "@/lib/api";
import type { SectorHeatmapResponse, SectorPerformance } from "@/types";
import { Treemap, ResponsiveContainer } from "recharts";

type Period = "1d" | "1w" | "1m";

function getPerformance(sector: SectorPerformance, period: Period): number {
  if (period === "1d") return sector.performance_1d;
  if (period === "1w") return sector.performance_1w;
  return sector.performance_1m;
}

function perfColor(perf: number): string {
  if (perf > 0.03) return "#059669";  // deep green
  if (perf > 0.01) return "#10b981";  // green
  if (perf > 0.002) return "#34d399"; // light green
  if (perf > -0.002) return "#6b7280"; // gray
  if (perf > -0.01) return "#f87171"; // light red
  if (perf > -0.03) return "#ef4444"; // red
  return "#dc2626"; // deep red
}

// Custom cell renderer for Treemap
const CustomCell = (props: any) => {
  const { x, y, width, height, name, perf } = props;
  if (width < 10 || height < 10) return null;

  const perfStr = `${perf >= 0 ? "+" : ""}${(perf * 100).toFixed(2)}%`;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={perfColor(perf)}
        stroke="var(--oracle-bg, #0a0e17)"
        strokeWidth={2}
        rx={4}
      />
      {width > 50 && height > 30 && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 6}
            textAnchor="middle"
            fill="white"
            fontSize={width > 80 ? 13 : 10}
            fontWeight="bold"
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            fill="rgba(255,255,255,0.85)"
            fontSize={width > 80 ? 12 : 9}
            fontFamily="monospace"
          >
            {perfStr}
          </text>
        </>
      )}
    </g>
  );
};

export default function SectorHeatmap() {
  const [data, setData] = useState<SectorHeatmapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>("1d");

  useEffect(() => {
    fetchAPI<SectorHeatmapResponse>("/api/v1/market/sectors/heatmap")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  const treemapData = (data?.sectors ?? []).map((s) => ({
    name: s.name,
    size: Math.max(s.market_cap_weight * 1000, 10),
    perf: getPerformance(s, period),
    symbol: s.symbol,
  }));

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          Sector Performance
        </h3>
        <div className="flex gap-1">
          {(["1d", "1w", "1m"] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`text-xs px-2 py-0.5 rounded transition-colors ${
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

      {error && <p className="text-oracle-red text-sm mb-2">{error}</p>}

      {loading && (
        <div className="animate-pulse h-64 bg-oracle-bg rounded" />
      )}

      {!loading && treemapData.length > 0 && (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={treemapData}
              dataKey="size"
              aspectRatio={4 / 3}
              content={<CustomCell />}
            />
          </ResponsiveContainer>
        </div>
      )}

      {/* Legend table below */}
      {!loading && data && data.sectors.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-oracle-muted text-left border-b border-oracle-border">
                <th className="pb-1 pr-2">Sector</th>
                <th className="pb-1 pr-2 text-right">1D</th>
                <th className="pb-1 pr-2 text-right">1W</th>
                <th className="pb-1 text-right">1M</th>
              </tr>
            </thead>
            <tbody>
              {data.sectors
                .sort((a, b) => getPerformance(b, period) - getPerformance(a, period))
                .map((s) => (
                  <tr key={s.symbol} className="border-t border-oracle-border/30">
                    <td className="py-1 pr-2">
                      <span className="text-oracle-text font-medium">{s.name}</span>
                      <span className="text-oracle-muted ml-1">({s.symbol})</span>
                    </td>
                    <td className={`py-1 pr-2 text-right font-mono ${s.performance_1d >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                      {s.performance_1d >= 0 ? "+" : ""}{(s.performance_1d * 100).toFixed(2)}%
                    </td>
                    <td className={`py-1 pr-2 text-right font-mono ${s.performance_1w >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                      {s.performance_1w >= 0 ? "+" : ""}{(s.performance_1w * 100).toFixed(2)}%
                    </td>
                    <td className={`py-1 text-right font-mono ${s.performance_1m >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                      {s.performance_1m >= 0 ? "+" : ""}{(s.performance_1m * 100).toFixed(2)}%
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
