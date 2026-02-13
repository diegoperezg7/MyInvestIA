"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";

interface SignalSummary {
  symbol: string;
  overall: string;
  overall_confidence: number;
  oscillators_rating: string;
  oscillators_buy: number;
  oscillators_sell: number;
  oscillators_neutral: number;
  moving_averages_rating: string;
  moving_averages_buy: number;
  moving_averages_sell: number;
  moving_averages_neutral: number;
  signals: Array<{
    direction: string;
    confidence: number;
    source: string;
    reasoning: string;
  }>;
}

const RATING_COLORS: Record<string, string> = {
  strong_buy: "text-oracle-green",
  buy: "text-oracle-green",
  neutral: "text-oracle-yellow",
  sell: "text-oracle-red",
  strong_sell: "text-oracle-red",
};

const RATING_BG: Record<string, string> = {
  strong_buy: "bg-oracle-green/10 border-oracle-green/30",
  buy: "bg-oracle-green/10 border-oracle-green/30",
  neutral: "bg-oracle-yellow/10 border-oracle-yellow/30",
  sell: "bg-oracle-red/10 border-oracle-red/30",
  strong_sell: "bg-oracle-red/10 border-oracle-red/30",
};

function Gauge({ label, rating, buy, sell, neutral }: {
  label: string;
  rating: string;
  buy: number;
  sell: number;
  neutral: number;
}) {
  const total = buy + sell + neutral;
  const buyPct = total > 0 ? (buy / total) * 100 : 0;
  const sellPct = total > 0 ? (sell / total) * 100 : 0;

  return (
    <div className="bg-oracle-bg rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-oracle-muted text-xs">{label}</span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded border ${RATING_BG[rating] || RATING_BG.neutral} ${RATING_COLORS[rating] || RATING_COLORS.neutral}`}>
          {rating.replace("_", " ").toUpperCase()}
        </span>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden bg-oracle-border mb-1">
        <div className="bg-oracle-green h-full" style={{ width: `${buyPct}%` }} />
        <div className="bg-oracle-yellow h-full" style={{ width: `${100 - buyPct - sellPct}%` }} />
        <div className="bg-oracle-red h-full" style={{ width: `${sellPct}%` }} />
      </div>
      <div className="flex justify-between text-[10px] text-oracle-muted">
        <span>Buy: {buy}</span>
        <span>Neutral: {neutral}</span>
        <span>Sell: {sell}</span>
      </div>
    </div>
  );
}

export default function SignalSummaryCard() {
  const [symbol, setSymbol] = useState("");
  const [data, setData] = useState<SignalSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetch = async () => {
    if (!symbol.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAPI<SignalSummary>(
        `/api/v1/market/signal-summary/${symbol.trim().toUpperCase()}`
      );
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load signals");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide mb-3">
        Signal Summary
      </h3>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleFetch()}
          placeholder="Symbol"
          className="flex-1 bg-oracle-bg border border-oracle-border rounded px-3 py-1.5 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent"
        />
        <button
          onClick={handleFetch}
          disabled={loading || !symbol.trim()}
          className="bg-oracle-accent text-white text-sm px-4 py-1.5 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "..." : "Signals"}
        </button>
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {data && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-oracle-text font-bold">{data.symbol}</span>
            <span className={`text-sm font-medium px-3 py-1 rounded border ${RATING_BG[data.overall] || RATING_BG.neutral} ${RATING_COLORS[data.overall] || RATING_COLORS.neutral}`}>
              {data.overall.replace("_", " ").toUpperCase()}
            </span>
            <span className="text-oracle-muted text-xs">
              {data.overall_confidence.toFixed(0)}% confidence
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3 mb-4">
            <Gauge
              label="Oscillators"
              rating={data.oscillators_rating}
              buy={data.oscillators_buy}
              sell={data.oscillators_sell}
              neutral={data.oscillators_neutral}
            />
            <Gauge
              label="Moving Averages"
              rating={data.moving_averages_rating}
              buy={data.moving_averages_buy}
              sell={data.moving_averages_sell}
              neutral={data.moving_averages_neutral}
            />
          </div>

          {data.signals.length > 0 && (
            <div className="space-y-1">
              <h4 className="text-oracle-muted text-xs uppercase mb-1">Individual Signals</h4>
              {data.signals.map((sig, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-oracle-text">{sig.source}</span>
                  <div className="flex items-center gap-2">
                    <span className={RATING_COLORS[sig.direction] || "text-oracle-muted"}>
                      {sig.direction.replace("_", " ").toUpperCase()}
                    </span>
                    <span className="text-oracle-muted">{sig.confidence.toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!data && !loading && !error && (
        <p className="text-oracle-muted text-sm">
          Enter a symbol to see aggregated buy/sell signals.
        </p>
      )}
    </div>
  );
}
