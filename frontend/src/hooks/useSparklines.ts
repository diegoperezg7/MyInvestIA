"use client";

import { useEffect, useRef, useState } from "react";
import { fetchAPI } from "@/lib/api";

type SparklineMap = Record<string, number[]>;

/**
 * Fetches sparkline data (7-day closing prices) for a list of symbols.
 * Returns a map of symbol -> number[].
 */
export default function useSparklines(symbols: string[]) {
  const [sparklines, setSparklines] = useState<SparklineMap>({});
  const prevKey = useRef("");

  useEffect(() => {
    if (symbols.length === 0) return;

    const key = [...symbols].sort().join(",");
    if (key === prevKey.current) return;
    prevKey.current = key;

    const chunks: string[][] = [];
    for (let i = 0; i < symbols.length; i += 20) {
      chunks.push(symbols.slice(i, i + 20));
    }

    Promise.all(
      chunks.map((chunk) =>
        fetchAPI<SparklineMap>(
          `/api/v1/market/sparklines?symbols=${chunk.join(",")}&days=7`
        ).catch(() => ({} as SparklineMap))
      )
    ).then((results) => {
      const merged: SparklineMap = {};
      for (const r of results) Object.assign(merged, r);
      setSparklines(merged);
    });
  }, [symbols]);

  return sparklines;
}
