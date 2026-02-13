"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { TechnicalAnalysis } from "@/types";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";

const SIGNAL_COLORS: Record<string, string> = {
  bullish: "text-oracle-green",
  bearish: "text-oracle-red",
  neutral: "text-oracle-yellow",
};

const SIGNAL_BG: Record<string, string> = {
  bullish: "bg-oracle-green/10 border-oracle-green/30",
  bearish: "bg-oracle-red/10 border-oracle-red/30",
  neutral: "bg-oracle-yellow/10 border-oracle-yellow/30",
};

function SignalBadge({ signal }: { signal: string }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${
        SIGNAL_BG[signal] || SIGNAL_BG.neutral
      } ${SIGNAL_COLORS[signal] || SIGNAL_COLORS.neutral}`}
    >
      {signal.toUpperCase()}
    </span>
  );
}

export default function TechnicalAnalysisCard() {
  const [symbol, setSymbol] = useState("");
  const [analysis, setAnalysis] = useState<TechnicalAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!symbol.trim()) return;
    setLoading(true);
    setError(null);
    setAnalysis(null);

    try {
      const data = await fetchAPI<TechnicalAnalysis>(
        `/api/v1/market/analysis/${symbol.trim().toUpperCase()}`
      );
      setAnalysis(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium mb-3 uppercase tracking-wide">
        Technical Analysis
      </h3>

      <div className="flex gap-2 mb-4">
        <SymbolAutocomplete
          value={symbol}
          onChange={setSymbol}
          onSubmit={(s) => { setSymbol(s); handleAnalyze(); }}
          placeholder="Enter symbol (e.g. AAPL)"
          className="flex-1"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading || !symbol.trim()}
          className="bg-oracle-accent text-white text-sm px-4 py-1.5 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "..." : "Analyze"}
        </button>
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {analysis && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <span className="text-oracle-text font-bold text-lg">
              {analysis.symbol}
            </span>
            <SignalBadge signal={analysis.overall_signal} />
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <IndicatorRow
              name="RSI"
              value={
                analysis.rsi.value !== null
                  ? analysis.rsi.value.toFixed(1)
                  : "--"
              }
              signal={analysis.rsi.signal}
            />
            <IndicatorRow
              name="MACD"
              value={
                analysis.macd.histogram !== null
                  ? analysis.macd.histogram.toFixed(4)
                  : "--"
              }
              signal={analysis.macd.signal}
            />
            <IndicatorRow
              name="SMA"
              value={
                analysis.sma.sma_20 !== null
                  ? analysis.sma.sma_20.toFixed(2)
                  : "--"
              }
              signal={analysis.sma.signal}
              label="20d"
            />
            <IndicatorRow
              name="EMA"
              value={
                analysis.ema.ema_12 !== null
                  ? analysis.ema.ema_12.toFixed(2)
                  : "--"
              }
              signal={analysis.ema.signal}
              label="12d"
            />
            <IndicatorRow
              name="Bollinger"
              value={
                analysis.bollinger_bands.bandwidth !== null
                  ? `${analysis.bollinger_bands.bandwidth.toFixed(1)}%`
                  : "--"
              }
              signal={analysis.bollinger_bands.signal}
              label="BW"
            />
            <div className="flex items-center gap-2 bg-oracle-bg rounded px-3 py-2">
              <span className="text-oracle-muted">Signals</span>
              <span className="text-oracle-green text-xs">
                {analysis.signal_counts.bullish}B
              </span>
              <span className="text-oracle-red text-xs">
                {analysis.signal_counts.bearish}S
              </span>
              <span className="text-oracle-yellow text-xs">
                {analysis.signal_counts.neutral}N
              </span>
            </div>
          </div>
        </div>
      )}

      {!analysis && !loading && !error && (
        <p className="text-oracle-muted text-sm">
          Enter a stock symbol to see technical indicators.
        </p>
      )}
    </div>
  );
}

function IndicatorRow({
  name,
  value,
  signal,
  label,
}: {
  name: string;
  value: string;
  signal: string;
  label?: string;
}) {
  return (
    <div className="flex items-center justify-between bg-oracle-bg rounded px-3 py-2">
      <div className="flex items-center gap-1.5">
        <span className="text-oracle-muted">{name}</span>
        {label && (
          <span className="text-oracle-muted text-xs">({label})</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-oracle-text font-mono text-xs">{value}</span>
        <span
          className={`w-2 h-2 rounded-full ${
            signal === "bullish"
              ? "bg-oracle-green"
              : signal === "bearish"
              ? "bg-oracle-red"
              : "bg-oracle-yellow"
          }`}
        />
      </div>
    </div>
  );
}
