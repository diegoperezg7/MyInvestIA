"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { AssetQuote } from "@/types";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";
import Sparkline from "@/components/ui/Sparkline";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useLanguageStore from "@/stores/useLanguageStore";
import { ChevronDown, ChevronUp } from "lucide-react";

function formatVolume(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toString();
}

export default function QuoteLookup({ defaultCollapsed = true }: { defaultCollapsed?: boolean }) {
  const [symbol, setSymbol] = useState("");
  const [quote, setQuote] = useState<AssetQuote | null>(null);
  const [sparkData, setSparkData] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const { formatPrice } = useCurrencyStore();
  const t = useLanguageStore((s) => s.t);

  const handleLookup = async (sym?: string) => {
    const target = (sym || symbol).trim().toUpperCase();
    if (!target) return;
    setLoading(true);
    setError(null);
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

  const isPositive = (quote?.change_percent ?? 0) >= 0;
  const hasContent = quote || error;

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      {/* Header row: title + search inline */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => hasContent && setCollapsed(!collapsed)}
          className="flex items-center gap-1.5 shrink-0"
        >
          <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
            {t("quote.title")}
          </h3>
          {hasContent && (
            collapsed
              ? <ChevronDown className="w-3.5 h-3.5 text-oracle-muted" />
              : <ChevronUp className="w-3.5 h-3.5 text-oracle-muted" />
          )}
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
          {error && <p className="text-oracle-red text-sm mb-2">{error}</p>}

          {quote && (
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="flex items-baseline gap-2 flex-1">
                  <span className="text-oracle-text font-bold text-lg">{quote.symbol}</span>
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
                <Sparkline data={sparkData} width={80} height={32} />
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
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
                {quote.market_cap > 0 && (
                  <div className="bg-oracle-bg rounded px-3 py-2 col-span-2">
                    <span className="text-oracle-muted text-xs">{t("quote.market_cap")}</span>
                    <p className="text-oracle-text font-mono">
                      {formatPrice(quote.market_cap, 0)}
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
