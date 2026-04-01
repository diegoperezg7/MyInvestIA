"use client";

import { useEffect, useState } from "react";
import { fetchAPI, postAPI } from "@/lib/api";
import Sparkline from "@/components/ui/Sparkline";
import useSparklines from "@/hooks/useSparklines";
import useCurrencyStore from "@/stores/useCurrencyStore";

interface ScreenerResult {
  symbol: string;
  name: string;
  close: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap: number;
  recommendation: string;
}

interface ScreenerResponse {
  results: ScreenerResult[];
  total: number;
  market: string;
}

interface Preset {
  id: string;
  name: string;
  description: string;
}

const MARKETS = ["america", "europe", "asia"] as const;

export default function ScreenerView() {
  const [results, setResults] = useState<ScreenerResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [market, setMarket] = useState<string>("america");
  const [presets, setPresets] = useState<Preset[]>([]);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minVolume, setMinVolume] = useState("");
  const { formatPrice } = useCurrencyStore();
  const [signal, setSignal] = useState("");

  const resultSymbols = results.map((r) => r.symbol);
  const sparklines = useSparklines(resultSymbols);

  const loadPresets = async () => {
    try {
      const data = await fetchAPI<{ presets: Preset[] }>("/api/v1/screener/presets");
      setPresets(data.presets);
    } catch { /* presets optional */ }
  };

  useEffect(() => {
    void loadPresets();
  }, []);

  const runScan = async (presetId?: string) => {
    setLoading(true);
    setError(null);
    try {
      const filters: Record<string, unknown> = {};
      if (minPrice) filters.min_price = parseFloat(minPrice);
      if (maxPrice) filters.max_price = parseFloat(maxPrice);
      if (minVolume) filters.min_volume = parseInt(minVolume);
      if (signal) filters.signal = signal;

      const data = await postAPI<ScreenerResponse>("/api/v1/screener/scan", {
        market,
        filters,
        preset_id: presetId || undefined,
        limit: 50,
      });
      setResults(data.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Screener scan failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <h3 className="text-oracle-muted text-xs font-medium uppercase mb-3">Filters</h3>

          <div className="space-y-3">
            <div>
              <label className="text-oracle-muted text-xs">Market</label>
              <select
                value={market}
                onChange={(e) => setMarket(e.target.value)}
                className="w-full mt-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
              >
                {MARKETS.map((m) => (
                  <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-oracle-muted text-xs">Min Price</label>
                <input
                  type="number"
                  value={minPrice}
                  onChange={(e) => setMinPrice(e.target.value)}
                  placeholder="0"
                  className="w-full mt-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
                />
              </div>
              <div>
                <label className="text-oracle-muted text-xs">Max Price</label>
                <input
                  type="number"
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(e.target.value)}
                  placeholder="&#8734;"
                  className="w-full mt-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
                />
              </div>
            </div>

            <div>
              <label className="text-oracle-muted text-xs">Min Volume</label>
              <input
                type="number"
                value={minVolume}
                onChange={(e) => setMinVolume(e.target.value)}
                placeholder="0"
                className="w-full mt-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
              />
            </div>

            <div>
              <label className="text-oracle-muted text-xs">Signal</label>
              <select
                value={signal}
                onChange={(e) => setSignal(e.target.value)}
                className="w-full mt-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
              >
                <option value="">All</option>
                <option value="strong_buy">Strong Buy</option>
                <option value="buy">Buy</option>
                <option value="neutral">Neutral</option>
                <option value="sell">Sell</option>
                <option value="strong_sell">Strong Sell</option>
              </select>
            </div>

            <button
              onClick={() => runScan()}
              disabled={loading}
              className="w-full bg-oracle-accent text-white text-sm py-2 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
            >
              {loading ? "Scanning..." : "Run Screener"}
            </button>
          </div>

          {presets.length > 0 && (
            <div className="mt-4 pt-3 border-t border-oracle-border">
              <h4 className="text-oracle-muted text-xs font-medium uppercase mb-2">Presets</h4>
              <div className="space-y-1">
                {presets.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => runScan(p.id)}
                    className="w-full text-left text-xs text-oracle-text hover:text-oracle-accent px-2 py-1.5 rounded hover:bg-oracle-bg transition-colors"
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-3 bg-oracle-panel border border-oracle-border rounded-lg p-4">
          {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

          {results.length === 0 && !loading && (
            <p className="text-oracle-muted text-sm text-center py-12">
              Configure filters and run the screener to find stocks.
            </p>
          )}

          {results.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-oracle-muted text-xs border-b border-oracle-border">
                    <th className="text-left py-2 px-2">Symbol</th>
                    <th className="text-left py-2 px-2">Name</th>
                    <th className="text-center py-2 px-2">7d</th>
                    <th className="text-right py-2 px-2">Price</th>
                    <th className="text-right py-2 px-2">Change</th>
                    <th className="text-right py-2 px-2">Volume</th>
                    <th className="text-center py-2 px-2">Signal</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r) => (
                    <tr key={r.symbol} className="border-b border-oracle-border/50 hover:bg-oracle-bg/50">
                      <td className="py-2 px-2 font-medium text-oracle-text">{r.symbol}</td>
                      <td className="py-2 px-2 text-oracle-text truncate max-w-[200px]">{r.name}</td>
                      <td className="py-2 px-2">
                        <Sparkline data={sparklines[r.symbol] ?? []} width={56} height={20} />
                      </td>
                      <td className="py-2 px-2 text-right text-oracle-text font-mono">{formatPrice(r.close)}</td>
                      <td className={`py-2 px-2 text-right font-mono ${r.change_percent >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                        {r.change_percent >= 0 ? "+" : ""}{r.change_percent.toFixed(2)}%
                      </td>
                      <td className="py-2 px-2 text-right text-oracle-muted font-mono">
                        {(r.volume / 1e6).toFixed(1)}M
                      </td>
                      <td className="py-2 px-2 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          r.recommendation?.includes("buy") ? "bg-oracle-green/10 text-oracle-green" :
                          r.recommendation?.includes("sell") ? "bg-oracle-red/10 text-oracle-red" :
                          "bg-oracle-yellow/10 text-oracle-yellow"
                        }`}>
                          {r.recommendation || "N/A"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
