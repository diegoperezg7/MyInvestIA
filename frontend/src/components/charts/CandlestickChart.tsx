"use client";

import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";

interface CandleData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Props {
  data: CandleData[];
  formatPrice?: (v: number, d?: number) => string;
}

export default function CandlestickChart({ data, formatPrice }: Props) {
  const fmt = formatPrice || ((v: number, d?: number) => `$${v.toFixed(d ?? 2)}`);
  if (!data.length) return null;

  // Calculate domain for Y axis with padding
  const prices = data.flatMap((d) => [d.high, d.low]);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = (maxPrice - minPrice) * 0.05;
  const yMin = minPrice - padding;
  const yMax = maxPrice + padding;
  const yRange = yMax - yMin;

  const chartData = data.map((d) => ({
    ...d,
    // Use body range as a bar value for rendering
    low_wick: Math.min(d.open, d.close) - d.low,
    body: Math.abs(d.close - d.open) || yRange * 0.002, // min height
    high_wick: d.high - Math.max(d.open, d.close),
    base: d.low,
    displayDate: new Date(d.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={chartData} barGap={0} barCategoryGap="20%">
        <XAxis
          dataKey="displayDate"
          tick={{ fill: "var(--oracle-muted)", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[yMin, yMax]}
          tick={{ fill: "var(--oracle-muted)", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          width={60}
          tickFormatter={(v: number) => fmt(v, 0)}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--oracle-panel)",
            border: "1px solid var(--oracle-border)",
            borderRadius: "8px",
            fontSize: "12px",
            color: "var(--oracle-text)",
          }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0]?.payload;
            if (!d) return null;
            const isGreen = d.close >= d.open;
            return (
              <div className="bg-oracle-panel border border-oracle-border rounded p-2 text-xs">
                <p className="text-oracle-text mb-1">{d.displayDate}</p>
                <p>O: <span className="text-oracle-text">{fmt(d.open)}</span></p>
                <p>H: <span className="text-oracle-text">{fmt(d.high)}</span></p>
                <p>L: <span className="text-oracle-text">{fmt(d.low)}</span></p>
                <p>C: <span className={isGreen ? "text-oracle-green" : "text-oracle-red"}>{fmt(d.close)}</span></p>
              </div>
            );
          }}
        />
        {/* Stacked bars: low_wick (transparent) + body (colored) + high_wick (transparent) */}
        <Bar dataKey="base" stackId="candle" fill="transparent" isAnimationActive={false} />
        <Bar dataKey="low_wick" stackId="candle" isAnimationActive={false}>
          {chartData.map((d, i) => (
            <Cell key={i} fill="transparent" stroke={d.close >= d.open ? "#10b981" : "#ef4444"} strokeWidth={1} />
          ))}
        </Bar>
        <Bar dataKey="body" stackId="candle" barSize={6} isAnimationActive={false}>
          {chartData.map((d, i) => (
            <Cell key={i} fill={d.close >= d.open ? "#10b981" : "#ef4444"} />
          ))}
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  );
}
