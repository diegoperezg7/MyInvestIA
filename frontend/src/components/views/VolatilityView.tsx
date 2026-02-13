"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";
import useCurrencyStore from "@/stores/useCurrencyStore";

interface VolatilityData {
  symbol: string;
  historical_volatility: number;
  atr: number;
  atr_percent: number;
  rsi: number;
  bollinger_bandwidth: number;
  daily_range: { high: number; low: number; range_percent: number };
  weekly_range: { high: number; low: number; range_percent: number };
  current_price: number;
  volatility_rating: "low" | "moderate" | "high" | "extreme";
}

const RATING_STYLES: Record<string, string> = {
  low: "bg-oracle-green/10 text-oracle-green border-oracle-green/30",
  moderate: "bg-oracle-yellow/10 text-oracle-yellow border-oracle-yellow/30",
  high: "bg-oracle-red/10 text-oracle-red border-oracle-red/30",
  extreme: "bg-oracle-red/20 text-oracle-red border-oracle-red/50",
};

export default function VolatilityView() {
  const [symbol, setSymbol] = useState("");
  const [data, setData] = useState<VolatilityData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [watchlist, setWatchlist] = useState<VolatilityData[]>([]);
  const { formatPrice } = useCurrencyStore();

  const fetchVolatility = async (sym: string) => {
    if (!sym.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAPI<VolatilityData>(
        `/api/v1/market/volatility/${sym.trim().toUpperCase()}`
      );
      setData(result);
      if (!watchlist.find((w) => w.symbol === result.symbol)) {
        setWatchlist((prev) => [...prev, result]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load volatility data");
    } finally {
      setLoading(false);
    }
  };

  const MetricCard = ({ label, value, suffix }: { label: string; value: string; suffix?: string }) => (
    <div className="bg-oracle-bg rounded-lg p-3">
      <p className="text-oracle-muted text-xs mb-1">{label}</p>
      <p className="text-oracle-text font-mono text-lg">
        {value}
        {suffix && <span className="text-oracle-muted text-sm ml-1">{suffix}</span>}
      </p>
    </div>
  );

  return (
    <div>
      <div className="flex gap-2 mb-6">
        <SymbolAutocomplete
          value={symbol}
          onChange={setSymbol}
          onSubmit={(s) => { setSymbol(s); fetchVolatility(s); }}
          placeholder="Enter symbol (e.g. AAPL)"
          className="flex-1 max-w-xs"
        />
        <button
          onClick={() => fetchVolatility(symbol)}
          disabled={loading || !symbol.trim()}
          className="bg-oracle-accent text-white text-sm px-4 py-2 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "Loading..." : "Analyze"}
        </button>
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {data && (
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h3 className="text-oracle-text font-bold text-lg">{data.symbol}</h3>
              <span className="text-oracle-text font-mono">{formatPrice(data.current_price)}</span>
            </div>
            <span className={`text-xs px-2 py-1 rounded border ${RATING_STYLES[data.volatility_rating]}`}>
              {data.volatility_rating.toUpperCase()} VOLATILITY
            </span>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
            <MetricCard label="Historical Volatility" value={`${(data.historical_volatility * 100).toFixed(1)}`} suffix="%" />
            <MetricCard label="ATR" value={data.atr.toFixed(2)} suffix={`(${data.atr_percent.toFixed(1)}%)`} />
            <MetricCard label="RSI" value={data.rsi.toFixed(1)} />
            <MetricCard label="Bollinger BW" value={`${data.bollinger_bandwidth.toFixed(1)}`} suffix="%" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div className="bg-oracle-bg rounded-lg p-3">
              <p className="text-oracle-muted text-xs mb-2">Daily Range</p>
              <div className="flex items-center justify-between">
                <span className="text-oracle-red text-sm font-mono">{formatPrice(data.daily_range.low)}</span>
                <div className="flex-1 mx-3 h-2 bg-oracle-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-oracle-accent rounded-full"
                    style={{
                      width: `${
                        data.daily_range.high !== data.daily_range.low
                          ? ((data.current_price - data.daily_range.low) / (data.daily_range.high - data.daily_range.low)) * 100
                          : 50
                      }%`,
                    }}
                  />
                </div>
                <span className="text-oracle-green text-sm font-mono">{formatPrice(data.daily_range.high)}</span>
              </div>
              <p className="text-oracle-muted text-xs mt-1 text-center">Range: {data.daily_range.range_percent.toFixed(2)}%</p>
            </div>

            <div className="bg-oracle-bg rounded-lg p-3">
              <p className="text-oracle-muted text-xs mb-2">Weekly Range</p>
              <div className="flex items-center justify-between">
                <span className="text-oracle-red text-sm font-mono">{formatPrice(data.weekly_range.low)}</span>
                <div className="flex-1 mx-3 h-2 bg-oracle-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-oracle-accent rounded-full"
                    style={{
                      width: `${
                        data.weekly_range.high !== data.weekly_range.low
                          ? ((data.current_price - data.weekly_range.low) / (data.weekly_range.high - data.weekly_range.low)) * 100
                          : 50
                      }%`,
                    }}
                  />
                </div>
                <span className="text-oracle-green text-sm font-mono">{formatPrice(data.weekly_range.high)}</span>
              </div>
              <p className="text-oracle-muted text-xs mt-1 text-center">Range: {data.weekly_range.range_percent.toFixed(2)}%</p>
            </div>
          </div>
        </div>
      )}

      {watchlist.length > 1 && (
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <h3 className="text-oracle-muted text-xs font-medium uppercase tracking-wide mb-3">
            Compared Assets
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-oracle-muted text-xs border-b border-oracle-border">
                  <th className="text-left py-2 px-2">Symbol</th>
                  <th className="text-right py-2 px-2">HV</th>
                  <th className="text-right py-2 px-2">ATR%</th>
                  <th className="text-right py-2 px-2">RSI</th>
                  <th className="text-right py-2 px-2">BB Width</th>
                  <th className="text-center py-2 px-2">Rating</th>
                </tr>
              </thead>
              <tbody>
                {watchlist.map((w) => (
                  <tr key={w.symbol} className="border-b border-oracle-border/50">
                    <td className="py-2 px-2 font-medium text-oracle-text">{w.symbol}</td>
                    <td className="py-2 px-2 text-right font-mono text-oracle-text">{(w.historical_volatility * 100).toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right font-mono text-oracle-text">{w.atr_percent.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right font-mono text-oracle-text">{w.rsi.toFixed(1)}</td>
                    <td className="py-2 px-2 text-right font-mono text-oracle-text">{w.bollinger_bandwidth.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded border ${RATING_STYLES[w.volatility_rating]}`}>
                        {w.volatility_rating}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!data && !loading && !error && (
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-12 text-center">
          <p className="text-oracle-muted text-sm">
            Enter a symbol to analyze its volatility metrics including Historical Volatility,
            ATR, RSI, Bollinger Bandwidth, and price ranges.
          </p>
        </div>
      )}
    </div>
  );
}
