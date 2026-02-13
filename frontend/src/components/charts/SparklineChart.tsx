"use client";

import { LineChart, Line, ResponsiveContainer } from "recharts";

interface Props {
  data: number[];
  positive?: boolean;
  width?: number;
  height?: number;
}

export default function SparklineChart({ data, positive = true, width, height }: Props) {
  const chartData = data.map((value, i) => ({ value, i }));
  const color = positive ? "#10b981" : "#ef4444";

  return (
    <ResponsiveContainer width={width || "100%"} height={height || "100%"}>
      <LineChart data={chartData}>
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
