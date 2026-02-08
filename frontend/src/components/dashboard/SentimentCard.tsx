"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { SentimentAnalysis } from "@/types";

const LABEL_COLORS: Record<string, string> = {
  bullish: "text-oracle-green",
  bearish: "text-oracle-red",
  neutral: "text-oracle-muted",
};

const LABEL_BG: Record<string, string> = {
  bullish: "bg-oracle-green/20 border-oracle-green/30",
  bearish: "bg-oracle-red/20 border-oracle-red/30",
  neutral: "bg-oracle-muted/20 border-oracle-muted/30",
};

function ScoreBar({ score }: { score: number }) {
  // score is -1.0 to 1.0, map to 0-100%
  const percent = ((score + 1) / 2) * 100;
  const barColor =
    score > 0.2
      ? "bg-oracle-green"
      : score < -0.2
        ? "bg-oracle-red"
        : "bg-oracle-accent";

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-oracle-muted mb-1">
        <span>Bearish</span>
        <span>Neutral</span>
        <span>Bullish</span>
      </div>
      <div className="relative h-2 bg-oracle-bg rounded-full overflow-hidden">
        {/* Center marker */}
        <div className="absolute left-1/2 top-0 w-px h-full bg-oracle-border z-10" />
        {/* Score indicator */}
        <div
          className={`absolute top-0 h-full w-3 rounded-full ${barColor}`}
          style={{ left: `calc(${percent}% - 6px)` }}
        />
      </div>
      <div className="text-center mt-1">
        <span className="text-sm font-mono text-white">
          {score > 0 ? "+" : ""}
          {score.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

export default function SentimentCard() {
  const [symbol, setSymbol] = useState("");
  const [data, setData] = useState<SentimentAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    const s = symbol.trim().toUpperCase();
    if (!s) return;

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const res = await fetchAPI<SentimentAnalysis>(
        `/api/v1/market/sentiment/${s}`
      );
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to analyze sentiment");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide mb-3">
        Sentiment Analysis
      </h3>

      {/* Search input */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
          placeholder="Enter symbol (e.g. AAPL)"
          className="flex-1 bg-oracle-bg border border-oracle-border rounded px-3 py-1.5 text-sm text-white placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading || !symbol.trim()}
          className="px-3 py-1.5 text-sm bg-oracle-accent/20 text-oracle-accent border border-oracle-accent/30 rounded hover:bg-oracle-accent/30 disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {data && (
        <div className="space-y-4">
          {/* Symbol + Label */}
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold text-white">{data.symbol}</span>
            <span
              className={`px-2 py-0.5 text-xs font-medium uppercase rounded border ${LABEL_BG[data.label]}`}
            >
              <span className={LABEL_COLORS[data.label]}>{data.label}</span>
            </span>
          </div>

          {/* Score bar */}
          <ScoreBar score={data.score} />

          {/* Narrative */}
          <p className="text-sm text-oracle-text leading-relaxed">
            {data.narrative}
          </p>

          {/* Key factors */}
          {data.key_factors.length > 0 && (
            <div>
              <p className="text-xs text-oracle-muted uppercase mb-1">
                Key Factors
              </p>
              <ul className="space-y-1">
                {data.key_factors.map((factor, i) => (
                  <li key={i} className="text-xs text-oracle-text flex gap-2">
                    <span className="text-oracle-accent shrink-0">*</span>
                    {factor}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Sources count */}
          {data.sources_count > 0 && (
            <p className="text-xs text-oracle-muted">
              Based on {data.sources_count} data points
            </p>
          )}
        </div>
      )}

      {!data && !loading && !error && (
        <p className="text-oracle-muted text-sm">
          Enter a symbol to get AI-powered sentiment analysis.
        </p>
      )}
    </div>
  );
}
