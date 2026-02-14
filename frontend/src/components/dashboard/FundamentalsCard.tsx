"use client";

import { useState, useEffect } from "react";
import { fetchAPI } from "@/lib/api";
import type { FundamentalsResponse } from "@/types";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";

function formatRatio(value: number, isPercent = false): string {
  if (!value || value === 0) return "N/A";
  if (isPercent) return `${(value * 100).toFixed(1)}%`;
  return value.toFixed(2);
}

function formatMarketCap(value: number): string {
  if (!value) return "N/A";
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`;
  return `$${value.toLocaleString()}`;
}

function RatioCell({ label, value, isPercent = false }: { label: string; value: number; isPercent?: boolean }) {
  const display = formatRatio(value, isPercent);
  const isGood = isPercent ? value > 0 : false;
  const isBad = isPercent ? value < 0 : false;
  return (
    <div>
      <p className="text-oracle-muted text-[10px] uppercase tracking-wide">{label}</p>
      <p className={`text-sm font-mono font-medium ${
        isGood ? "text-oracle-green" : isBad ? "text-oracle-red" : "text-oracle-text"
      }`}>
        {display}
      </p>
    </div>
  );
}

export default function FundamentalsCard({ symbol: initialSymbol }: { symbol?: string }) {
  const [symbol, setSymbol] = useState(initialSymbol || "AAPL");
  const [searchValue, setSearchValue] = useState("");
  const [data, setData] = useState<FundamentalsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (sym: string) => {
    const target = sym.trim().toUpperCase();
    if (!target) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAPI<FundamentalsResponse>(
        `/api/v1/market/fundamentals/${target}`
      );
      setData(result);
      setSymbol(target);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load fundamentals");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(symbol);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          Fundamentals
        </h3>
      </div>

      <div className="flex gap-2 mb-3">
        <SymbolAutocomplete
          value={searchValue}
          onChange={setSearchValue}
          onSubmit={(s) => { setSearchValue(s); fetchData(s); }}
          placeholder="Search symbol..."
          className="flex-1"
        />
        <button
          onClick={() => fetchData(searchValue)}
          disabled={loading || !searchValue.trim()}
          className="bg-oracle-accent text-white text-sm px-3 py-1 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "..." : "Load"}
        </button>
      </div>

      {error && <p className="text-oracle-red text-sm mb-2">{error}</p>}

      {loading && !data && (
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-oracle-bg rounded w-32" />
          <div className="h-20 bg-oracle-bg rounded" />
        </div>
      )}

      {data && (
        <div>
          {/* Company header */}
          <div className="mb-3">
            <div className="flex items-baseline gap-2">
              <span className="text-oracle-text font-bold text-lg">{data.symbol}</span>
              <span className="text-oracle-muted text-sm">{data.company_info.name}</span>
            </div>
            <div className="flex gap-2 mt-1 text-xs text-oracle-muted">
              <span>{data.company_info.sector}</span>
              {data.company_info.industry && <span>/ {data.company_info.industry}</span>}
              <span>/ {formatMarketCap(data.company_info.market_cap)}</span>
            </div>
          </div>

          {/* Ratios grid */}
          <div className="grid grid-cols-3 gap-x-4 gap-y-2 mb-4">
            <div className="col-span-3 text-oracle-muted text-[10px] font-semibold uppercase tracking-widest border-b border-oracle-border pb-1">
              Valuation
            </div>
            <RatioCell label="P/E" value={data.ratios.pe_trailing} />
            <RatioCell label="Fwd P/E" value={data.ratios.pe_forward} />
            <RatioCell label="P/B" value={data.ratios.price_to_book} />
            <RatioCell label="P/S" value={data.ratios.price_to_sales} />
            <RatioCell label="EV/EBITDA" value={data.ratios.ev_to_ebitda} />
            <RatioCell label="Beta" value={data.ratios.beta} />

            <div className="col-span-3 text-oracle-muted text-[10px] font-semibold uppercase tracking-widest border-b border-oracle-border pb-1 mt-2">
              Profitability
            </div>
            <RatioCell label="ROE" value={data.ratios.roe} isPercent />
            <RatioCell label="Profit Margin" value={data.ratios.profit_margins} isPercent />
            <RatioCell label="Op. Margin" value={data.ratios.operating_margins} isPercent />
            <RatioCell label="Gross Margin" value={data.ratios.gross_margins} isPercent />
            <RatioCell label="D/E" value={data.ratios.debt_to_equity} />
            <RatioCell label="Current Ratio" value={data.ratios.current_ratio} />

            <div className="col-span-3 text-oracle-muted text-[10px] font-semibold uppercase tracking-widest border-b border-oracle-border pb-1 mt-2">
              Growth (YoY)
            </div>
            <RatioCell label="Revenue" value={data.growth.revenue_growth} isPercent />
            <RatioCell label="Earnings" value={data.growth.earnings_growth} isPercent />
            <RatioCell label="Div Yield" value={data.ratios.dividend_yield} isPercent />
          </div>

          {/* Peers */}
          {data.peers.length > 0 && (
            <div>
              <h4 className="text-oracle-muted text-[10px] font-semibold uppercase tracking-widest border-b border-oracle-border pb-1 mb-2">
                Peer Comparison
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-oracle-muted text-left">
                      <th className="pb-1 pr-2">Symbol</th>
                      <th className="pb-1 pr-2">P/E</th>
                      <th className="pb-1 pr-2">P/B</th>
                      <th className="pb-1 pr-2">ROE</th>
                      <th className="pb-1 pr-2">Margin</th>
                      <th className="pb-1">Mkt Cap</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.peers.map((peer) => (
                      <tr key={peer.symbol} className="text-oracle-text border-t border-oracle-border/50">
                        <td className="py-1 pr-2 font-medium">{peer.symbol}</td>
                        <td className="py-1 pr-2 font-mono">{formatRatio(peer.pe_trailing)}</td>
                        <td className="py-1 pr-2 font-mono">{formatRatio(peer.price_to_book)}</td>
                        <td className="py-1 pr-2 font-mono">{formatRatio(peer.roe, true)}</td>
                        <td className="py-1 pr-2 font-mono">{formatRatio(peer.profit_margins, true)}</td>
                        <td className="py-1 font-mono">{formatMarketCap(peer.market_cap)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
