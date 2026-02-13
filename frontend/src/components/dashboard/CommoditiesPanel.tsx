"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAPI } from "@/lib/api";
import useCurrencyStore from "@/stores/useCurrencyStore";
import Sparkline from "@/components/ui/Sparkline";
import useSparklines from "@/hooks/useSparklines";

interface CommodityItem {
  symbol: string;
  name: string;
  category: string;
  price: number;
  change_percent: number;
  volume: number;
}

interface CommoditiesResponse {
  commodities: CommodityItem[];
  by_category: Record<string, CommodityItem[]>;
}

const CATEGORY_LABELS: Record<string, string> = {
  metals: "Precious Metals",
  energy: "Energy",
  agriculture: "Agriculture",
};

const CATEGORY_ORDER = ["metals", "energy", "agriculture"];
const REFRESH_INTERVAL = 15_000;

export default function CommoditiesPanel() {
  const [data, setData] = useState<CommoditiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { formatPrice } = useCurrencyStore();

  const allSymbols = data?.commodities.map((c) => c.symbol) ?? [];
  const sparklines = useSparklines(allSymbols);

  const refresh = useCallback(() => {
    fetchAPI<CommoditiesResponse>("/api/v1/market/commodities")
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
    intervalRef.current = setInterval(refresh, REFRESH_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [refresh]);

  if (loading) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6 animate-pulse">
        <div className="h-4 bg-oracle-border rounded w-32 mb-4" />
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-5 bg-oracle-border/40 rounded w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
        <p className="text-oracle-red text-sm">Failed to load commodities</p>
      </div>
    );
  }

  const byCategory = data?.by_category ?? {};

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium mb-4 uppercase tracking-wide">
        Commodities
      </h3>

      {CATEGORY_ORDER.map((cat) => {
        const items = byCategory[cat];
        if (!items || items.length === 0) return null;
        return (
          <div key={cat} className="mb-4 last:mb-0">
            <h4 className="text-oracle-accent text-xs font-medium mb-2">
              {CATEGORY_LABELS[cat] || cat}
            </h4>
            <div className="space-y-0.5">
              {items.map((item) => (
                <div
                  key={item.symbol}
                  className="flex items-center justify-between text-sm py-1"
                >
                  <div className="flex items-center gap-2 min-w-[80px]">
                    <span className="font-medium text-oracle-text w-16 truncate">
                      {item.symbol}
                    </span>
                    <span className="text-oracle-muted text-xs truncate max-w-[80px] hidden sm:inline">
                      {item.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Sparkline
                      data={sparklines[item.symbol] ?? []}
                      width={48}
                      height={18}
                    />
                    <span className="text-oracle-text font-mono text-xs">
                      {formatPrice(item.price)}
                    </span>
                    <span
                      className={`text-xs font-mono font-medium w-16 text-right ${
                        item.change_percent >= 0
                          ? "text-oracle-green"
                          : "text-oracle-red"
                      }`}
                    >
                      {item.change_percent >= 0 ? "+" : ""}
                      {item.change_percent.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {(!data || data.commodities.length === 0) && (
        <p className="text-oracle-muted text-sm">Commodity data unavailable</p>
      )}
    </div>
  );
}
