"use client";

import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { MarketOverview } from "@/types";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export default function MarketOverviewCard() {
  const [market, setMarket] = useState<MarketOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAPI<MarketOverview>("/api/v1/market/")
      .then(setMarket)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6 animate-pulse">
        <div className="h-4 bg-oracle-border rounded w-32 mb-4" />
        <div className="space-y-3">
          <div className="h-6 bg-oracle-border rounded w-full" />
          <div className="h-6 bg-oracle-border rounded w-full" />
          <div className="h-6 bg-oracle-border rounded w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
        <p className="text-oracle-red text-sm">Failed to load market data</p>
      </div>
    );
  }

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium mb-4 uppercase tracking-wide">
        Market Movers
      </h3>

      {market && market.top_gainers.length > 0 && (
        <div className="mb-4">
          <h4 className="text-oracle-green text-xs font-medium mb-2">
            Top Gainers
          </h4>
          <div className="space-y-1.5">
            {market.top_gainers.slice(0, 5).map((asset) => (
              <div
                key={asset.symbol}
                className="flex items-center justify-between text-sm"
              >
                <span className="font-medium text-white">{asset.symbol}</span>
                <div className="flex items-center gap-3">
                  <span className="text-oracle-text">
                    {formatCurrency(asset.price)}
                  </span>
                  <span className="text-oracle-green text-xs font-medium w-16 text-right">
                    +{asset.change_percent.toFixed(2)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {market && market.top_losers.length > 0 && (
        <div>
          <h4 className="text-oracle-red text-xs font-medium mb-2">
            Top Losers
          </h4>
          <div className="space-y-1.5">
            {market.top_losers.slice(0, 5).map((asset) => (
              <div
                key={asset.symbol}
                className="flex items-center justify-between text-sm"
              >
                <span className="font-medium text-white">{asset.symbol}</span>
                <div className="flex items-center gap-3">
                  <span className="text-oracle-text">
                    {formatCurrency(asset.price)}
                  </span>
                  <span className="text-oracle-red text-xs font-medium w-16 text-right">
                    {asset.change_percent.toFixed(2)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {market &&
        market.top_gainers.length === 0 &&
        market.top_losers.length === 0 && (
          <p className="text-oracle-muted text-sm">
            Market data unavailable
          </p>
        )}
    </div>
  );
}
