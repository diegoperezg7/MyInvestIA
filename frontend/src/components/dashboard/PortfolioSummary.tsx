"use client";

import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { Portfolio } from "@/types";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export default function PortfolioSummary() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAPI<Portfolio>("/api/v1/portfolio/")
      .then(setPortfolio)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6 animate-pulse">
        <div className="h-4 bg-oracle-border rounded w-24 mb-3" />
        <div className="h-8 bg-oracle-border rounded w-32" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
        <p className="text-oracle-red text-sm">Failed to load portfolio</p>
      </div>
    );
  }

  const pnlColor =
    (portfolio?.daily_pnl ?? 0) >= 0 ? "text-oracle-green" : "text-oracle-red";

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium mb-1">
        Portfolio Value
      </h3>
      <p className="text-3xl font-bold text-white">
        {portfolio ? formatCurrency(portfolio.total_value) : "--"}
      </p>

      <div className="mt-3 flex items-center gap-3">
        <span className={`text-sm font-medium ${pnlColor}`}>
          {portfolio ? formatCurrency(portfolio.daily_pnl) : "--"}
        </span>
        <span className={`text-sm ${pnlColor}`}>
          {portfolio ? formatPercent(portfolio.daily_pnl_percent) : "--"}
        </span>
        <span className="text-oracle-muted text-xs">today</span>
      </div>

      {portfolio && portfolio.holdings.length > 0 && (
        <div className="mt-4 border-t border-oracle-border pt-3">
          <h4 className="text-oracle-muted text-xs font-medium mb-2 uppercase tracking-wide">
            Holdings ({portfolio.holdings.length})
          </h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {portfolio.holdings.map((h) => (
              <div
                key={h.asset.symbol}
                className="flex items-center justify-between text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium text-white">
                    {h.asset.symbol}
                  </span>
                  <span className="text-oracle-muted text-xs">
                    {h.quantity} shares
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-white">
                    {formatCurrency(h.current_value)}
                  </span>
                  <span
                    className={`ml-2 text-xs ${
                      h.unrealized_pnl >= 0
                        ? "text-oracle-green"
                        : "text-oracle-red"
                    }`}
                  >
                    {formatPercent(h.unrealized_pnl_percent)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {portfolio && portfolio.holdings.length === 0 && (
        <p className="mt-4 text-oracle-muted text-sm">
          No holdings yet. Add assets to your portfolio.
        </p>
      )}
    </div>
  );
}
