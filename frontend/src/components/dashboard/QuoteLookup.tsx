"use client";

import { useState, useEffect, useRef } from "react";
import { fetchAPI } from "@/lib/api";
import type { AssetQuote } from "@/types";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";
import Sparkline from "@/components/ui/Sparkline";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useLanguageStore from "@/stores/useLanguageStore";
import { ChevronDown, ChevronUp, Search } from "lucide-react";

const QUICK_PICKS = [
  { symbol: "SPY", label: "SPY" },
  { symbol: "QQQ", label: "QQQ" },
  { symbol: "AAPL", label: "AAPL" },
  { symbol: "TSLA", label: "TSLA" },
  { symbol: "BTC-USD", label: "BTC" },
  { symbol: "ETH-USD", label: "ETH" },
];

const DEFAULT_SYMBOL = "SPY";

function formatVolume(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toString();
}

export default function QuoteLookup({ defaultCollapsed = false }: { defaultCollapsed?: boolean }) {
  const [symbol, setSymbol] = useState("");
  const [quote, setQuote] = useState<AssetQuote | null>(null);
  const [sparkData, setSparkData] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [activeSymbol, setActiveSymbol] = useState<string>("");
  const { formatPrice } = useCurrencyStore();
  const t = useLanguageStore((s) => s.t);
  const didMount = useRef(false);

  const handleLookup = async (sym?: string) => {
    const target = (sym || symbol).trim().toUpperCase();
    if (!target) return;
    setLoading(true);
    setError(null);
    setActiveSymbol(target);
    try {
      const [data, sparklines] = await Promise.all([
        fetchAPI<AssetQuote>(`/api/v1/market/quote/${target}`),
        fetchAPI<Record<string, number[]>>(
          `/api/v1/market/sparklines?symbols=${encodeURIComponent(target)}&days=7`
        ).catch(() => ({} as Record<string, number[]>)),
      ]);
      setQuote(data);
      setSparkData(sparklines[target] ?? sparklines[Object.keys(sparklines)[0]] ?? []);
      setCollapsed(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Quote lookup failed");
      setQuote(null);
      setSparkData([]);
    } finally {
      setLoading(false);
    }
  };

  // Auto-load default quote on mount
  useEffect(() => {
    if (!didMount.current) {
      didMount.current = true;
      handleLookup(DEFAULT_SYMBOL);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isPositive = (quote?.change_percent ?? 0) >= 0;

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      {/* Header row: title + search inline */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-1.5 shrink-0"
        >
          <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
            {t("quote.title")}
          </h3>
          {collapsed
            ? <ChevronDown className="w-3.5 h-3.5 text-oracle-muted" />
            : <ChevronUp className="w-3.5 h-3.5 text-oracle-muted" />
          }
        </button>

        <div className="flex gap-2 flex-1">
          <SymbolAutocomplete
            value={symbol}
            onChange={setSymbol}
            onSubmit={(s) => { setSymbol(s); handleLookup(s); }}
            placeholder={t("quote.placeholder")}
            className="flex-1"
            size="sm"
          />
          <button
            onClick={() => handleLookup()}
            disabled={loading || !symbol.trim()}
            className="bg-oracle-accent text-white text-xs px-3 py-1 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
          >
            {loading ? "..." : t("quote.get")}
          </button>
        </div>
      </div>

      {/* Collapsible content */}
      {!collapsed && (
        <div className="mt-3">
          {/* Quick picks row */}
          <div className="flex items-center gap-1.5 mb-3 flex-wrap">
            <Search className="w-3 h-3 text-oracle-muted shrink-0" />
            {QUICK_PICKS.map((pick) => (
              <button
                key={pick.symbol}
                onClick={() => { setSymbol(pick.symbol); handleLookup(pick.symbol); }}
                className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                  activeSymbol === pick.symbol
                    ? "bg-oracle-accent/20 text-oracle-accent border-oracle-accent/40"
                    : "bg-oracle-bg text-oracle-muted border-oracle-border hover:text-oracle-text hover:border-oracle-accent/30"
                }`}
              >
                {pick.label}
              </button>
            ))}
          </div>

          {error && <p className="text-oracle-red text-sm mb-2">{error}</p>}

          {/* Loading skeleton */}
          {loading && !quote && (
            <div className="animate-pulse space-y-3">
              <div className="flex items-center gap-3">
                <div className="h-7 w-16 bg-oracle-bg rounded" />
                <div className="h-8 w-28 bg-oracle-bg rounded" />
                <div className="h-5 w-14 bg-oracle-bg rounded" />
                <div className="ml-auto h-8 w-20 bg-oracle-bg rounded" />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="h-14 bg-oracle-bg rounded" />
                <div className="h-14 bg-oracle-bg rounded" />
                <div className="h-14 bg-oracle-bg rounded" />
              </div>
            </div>
          )}

          {quote && (
            <div>
              {/* Price header */}
              <div className="flex items-center gap-3 mb-3">
                <div className="flex items-baseline gap-2 flex-1 min-w-0">
                  <span className="text-oracle-text font-bold text-lg">{quote.symbol}</span>
                  {quote.name && quote.name !== quote.symbol && (
                    <span className="text-oracle-muted text-xs truncate">{quote.name}</span>
                  )}
                </div>
                <div className="flex items-baseline gap-2 shrink-0">
                  <span className="text-oracle-text text-2xl font-mono">
                    {formatPrice(quote.price)}
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
              </div>

              {/* Sparkline */}
              {sparkData.length > 0 && (
                <div className="mb-3 bg-oracle-bg rounded-lg p-2">
                  <div className="w-full h-12">
                    <Sparkline data={sparkData} width={400} height={48} className="!w-full" />
                  </div>
                  <p className="text-[10px] text-oracle-muted text-right mt-0.5">7d</p>
                </div>
              )}

              {/* Stats grid */}
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div className="bg-oracle-bg rounded px-3 py-2">
                  <span className="text-oracle-muted text-xs">{t("quote.prev_close")}</span>
                  <p className="text-oracle-text font-mono">
                    {formatPrice(quote.previous_close)}
                  </p>
                </div>
                <div className="bg-oracle-bg rounded px-3 py-2">
                  <span className="text-oracle-muted text-xs">{t("quote.volume")}</span>
                  <p className="text-oracle-text font-mono">
                    {formatVolume(quote.volume)}
                  </p>
                </div>
                {(quote.market_cap ?? 0) > 0 ? (
                  <div className="bg-oracle-bg rounded px-3 py-2">
                    <span className="text-oracle-muted text-xs">{t("quote.market_cap")}</span>
                    <p className="text-oracle-text font-mono">
                      {formatPrice(quote.market_cap ?? 0, 0)}
                    </p>
                  </div>
                ) : (
                  <div className="bg-oracle-bg rounded px-3 py-2">
                    <span className="text-oracle-muted text-xs">{t("quote.day_range")}</span>
                    <p className="text-oracle-text font-mono text-xs mt-0.5">
                      {formatPrice(quote.previous_close)} – {formatPrice(quote.price)}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
