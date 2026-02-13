"use client";

import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";
import SparklineChart from "@/components/charts/SparklineChart";
import useCurrencyStore from "@/stores/useCurrencyStore";

interface Mover {
  symbol: string;
  name: string;
  price: number;
  change_percent: number;
  volume: number;
  sparkline: number[];
}

interface MoversResponse {
  gainers: Mover[];
  losers: Mover[];
}

export default function MoversView() {
  const [data, setData] = useState<MoversResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [region, setRegion] = useState("us");
  const [threshold, setThreshold] = useState(1);

  const fetchMovers = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAPI<MoversResponse>(
        `/api/v1/market/movers?region=${region}&threshold=${threshold}`
      );
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load movers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMovers();
  }, [region, threshold]);

  const { formatPrice } = useCurrencyStore();

  const MoverRow = ({ mover, isGainer }: { mover: Mover; isGainer: boolean }) => (
    <div className="flex items-center justify-between py-2 px-3 hover:bg-oracle-bg/50 rounded transition-colors">
      <div className="flex items-center gap-3 min-w-[120px]">
        <span className="font-medium text-oracle-text text-sm">{mover.symbol}</span>
        <span className="text-oracle-muted text-xs truncate max-w-[100px]">{mover.name}</span>
      </div>
      <div className="w-24 h-8">
        {mover.sparkline?.length > 1 && (
          <SparklineChart data={mover.sparkline} positive={isGainer} />
        )}
      </div>
      <div className="flex items-center gap-4 min-w-[180px] justify-end">
        <span className="text-oracle-text font-mono text-sm">{formatPrice(mover.price)}</span>
        <span
          className={`font-mono text-sm font-medium w-20 text-right ${
            isGainer ? "text-oracle-green" : "text-oracle-red"
          }`}
        >
          {isGainer ? "+" : ""}{mover.change_percent.toFixed(2)}%
        </span>
        <span className="text-oracle-muted text-xs font-mono w-16 text-right">
          {(mover.volume / 1e6).toFixed(1)}M
        </span>
      </div>
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-end mb-4">
        <div className="flex items-center gap-3">
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="bg-oracle-bg border border-oracle-border rounded px-2 py-1 text-sm text-oracle-text"
          >
            <option value="all">All Markets</option>
            <option value="us">US Market</option>
            <option value="eu">Europe</option>
            <option value="asia">Asia</option>
            <option value="latam">LATAM</option>
            <option value="crypto">Crypto</option>
          </select>
          <select
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="bg-oracle-bg border border-oracle-border rounded px-2 py-1 text-sm text-oracle-text"
          >
            <option value={0.5}>0.5%+ moves</option>
            <option value={1}>1%+ moves</option>
            <option value={2}>2%+ moves</option>
            <option value={5}>5%+ moves</option>
            <option value={10}>10%+ moves</option>
          </select>
          <button
            onClick={fetchMovers}
            disabled={loading}
            className="bg-oracle-accent text-white text-sm px-3 py-1 rounded hover:bg-oracle-accent/80 disabled:opacity-50"
          >
            {loading ? "..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <h3 className="text-oracle-green text-sm font-medium mb-3 uppercase tracking-wide">
            Top Gainers
          </h3>
          {loading && (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-oracle-border/30 rounded animate-pulse" />
              ))}
            </div>
          )}
          {data && data.gainers.length === 0 && (
            <p className="text-oracle-muted text-sm">No gainers above threshold</p>
          )}
          {data?.gainers.map((m) => (
            <MoverRow key={m.symbol} mover={m} isGainer={true} />
          ))}
        </div>

        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <h3 className="text-oracle-red text-sm font-medium mb-3 uppercase tracking-wide">
            Top Losers
          </h3>
          {loading && (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-oracle-border/30 rounded animate-pulse" />
              ))}
            </div>
          )}
          {data && data.losers.length === 0 && (
            <p className="text-oracle-muted text-sm">No losers above threshold</p>
          )}
          {data?.losers.map((m) => (
            <MoverRow key={m.symbol} mover={m} isGainer={false} />
          ))}
        </div>
      </div>
    </div>
  );
}
