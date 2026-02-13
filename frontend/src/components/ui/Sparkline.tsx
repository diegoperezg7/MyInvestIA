"use client";

import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  className?: string;
}

export default function Sparkline({
  data,
  width = 60,
  height = 24,
  className = "",
}: SparklineProps) {
  if (!data || data.length < 2) return null;

  const isPositive = data[data.length - 1] >= data[0];
  const color = isPositive ? "#10b981" : "#ef4444";
  const gradientId = `spark-${Math.random().toString(36).slice(2, 8)}`;

  const chartData = data.map((close, i) => ({ i, close }));

  return (
    <div className={`shrink-0 ${className}`} style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 1, right: 0, bottom: 1, left: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="close"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
