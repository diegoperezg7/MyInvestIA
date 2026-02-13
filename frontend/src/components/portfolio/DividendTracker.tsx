"use client";

import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";
import useCurrencyStore from "@/stores/useCurrencyStore";

interface DividendData {
  dividends: Record<string, Array<{ date: string; amount: number; symbol: string }>>;
  total_annual: number;
  symbols_with_dividends: number;
}

export default function DividendTracker() {
  const [data, setData] = useState<DividendData | null>(null);
  const [loading, setLoading] = useState(true);
  const { formatPrice } = useCurrencyStore();

  useEffect(() => {
    fetchAPI<DividendData>("/api/v1/portfolio/dividends")
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-oracle-muted text-sm animate-pulse">Loading dividends...</div>;
  if (!data) return null;

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      <h3 className="text-oracle-muted text-xs font-medium uppercase tracking-wide mb-3">
        Dividend Tracker
      </h3>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-oracle-bg rounded p-2">
          <p className="text-oracle-muted text-xs">Annual Dividends</p>
          <p className="text-oracle-green font-mono text-lg">{formatPrice(data.total_annual)}</p>
        </div>
        <div className="bg-oracle-bg rounded p-2">
          <p className="text-oracle-muted text-xs">Paying Stocks</p>
          <p className="text-oracle-text font-mono text-lg">{data.symbols_with_dividends}</p>
        </div>
      </div>

      {Object.entries(data.dividends).map(([symbol, divs]) =>
        divs.length > 0 ? (
          <div key={symbol} className="mb-2">
            <h4 className="text-oracle-text text-xs font-medium mb-1">{symbol}</h4>
            <div className="space-y-0.5">
              {divs.slice(-4).map((d, i) => (
                <div key={i} className="flex justify-between text-xs text-oracle-muted">
                  <span>{new Date(d.date).toLocaleDateString()}</span>
                  <span className="text-oracle-green">{formatPrice(d.amount, 4)}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null
      )}

      {data.symbols_with_dividends === 0 && (
        <p className="text-oracle-muted text-sm">No dividend-paying stocks in portfolio.</p>
      )}
    </div>
  );
}
