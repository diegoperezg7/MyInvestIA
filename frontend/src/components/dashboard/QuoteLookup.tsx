"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { AssetQuote } from "@/types";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatVolume(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toString();
}

export default function QuoteLookup() {
  const [symbol, setSymbol] = useState("");
  const [quote, setQuote] = useState<AssetQuote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLookup = async () => {
    if (!symbol.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAPI<AssetQuote>(
        `/api/v1/market/quote/${symbol.trim().toUpperCase()}`
      );
      setQuote(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Quote lookup failed");
      setQuote(null);
    } finally {
      setLoading(false);
    }
  };

  const isPositive = (quote?.change_percent ?? 0) >= 0;

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium mb-3 uppercase tracking-wide">
        Quote Lookup
      </h3>

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLookup()}
          placeholder="Symbol (e.g. NVDA, BTC)"
          className="flex-1 bg-oracle-bg border border-oracle-border rounded px-3 py-1.5 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent"
        />
        <button
          onClick={handleLookup}
          disabled={loading || !symbol.trim()}
          className="bg-oracle-accent text-white text-sm px-4 py-1.5 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "..." : "Get"}
        </button>
      </div>

      {error && <p className="text-oracle-red text-sm mb-2">{error}</p>}

      {quote && (
        <div>
          <div className="flex items-baseline gap-2 mb-3">
            <span className="text-white font-bold text-lg">{quote.symbol}</span>
            <span className="text-white text-2xl font-mono">
              {formatCurrency(quote.price)}
            </span>
            <span
              className={`text-sm font-medium ${
                isPositive ? "text-oracle-green" : "text-oracle-red"
              }`}
            >
              {isPositive ? "+" : ""}
              {quote.change_percent.toFixed(2)}%
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-oracle-bg rounded px-3 py-2">
              <span className="text-oracle-muted text-xs">Prev Close</span>
              <p className="text-white font-mono">
                {formatCurrency(quote.previous_close)}
              </p>
            </div>
            <div className="bg-oracle-bg rounded px-3 py-2">
              <span className="text-oracle-muted text-xs">Volume</span>
              <p className="text-white font-mono">
                {formatVolume(quote.volume)}
              </p>
            </div>
            {quote.market_cap > 0 && (
              <div className="bg-oracle-bg rounded px-3 py-2 col-span-2">
                <span className="text-oracle-muted text-xs">Market Cap</span>
                <p className="text-white font-mono">
                  {formatCurrency(quote.market_cap)}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {!quote && !loading && !error && (
        <p className="text-oracle-muted text-sm">
          Look up real-time quotes for stocks, ETFs, and crypto.
        </p>
      )}
    </div>
  );
}
