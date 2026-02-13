"use client";

import { useEffect, useState, useRef } from "react";
import { fetchAPI, postAPI, deleteAPI } from "@/lib/api";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useLanguageStore from "@/stores/useLanguageStore";
import Sparkline from "@/components/ui/Sparkline";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";
import useSparklines from "@/hooks/useSparklines";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { WatchlistList, Watchlist, Asset } from "@/types";

export default function WatchlistCard({ defaultCollapsed = true }: { defaultCollapsed?: boolean }) {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [addSymbol, setAddSymbol] = useState<Record<string, string>>({});
  const [addType, setAddType] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const { formatPrice } = useCurrencyStore();
  const t = useLanguageStore((s) => s.t);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Gather symbols from the expanded watchlist for sparklines
  const expandedWl = watchlists.find((wl) => wl.id === expandedId);
  const expandedSymbols = expandedWl?.assets.map((a: Asset) => a.symbol) ?? [];
  const sparklines = useSparklines(expandedSymbols);

  const totalAssets = watchlists.reduce((acc, wl) => acc + wl.assets.length, 0);

  const loadWatchlists = () => {
    fetchAPI<WatchlistList>("/api/v1/watchlists/")
      .then((data) => setWatchlists(data.watchlists))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadWatchlists();
    intervalRef.current = setInterval(loadWatchlists, 60_000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const wl = await postAPI<Watchlist>("/api/v1/watchlists/", { name: newName.trim() });
      setNewName("");
      setExpandedId(wl.id);
      setCollapsed(false);
      loadWatchlists();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("msg.failed_create"));
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteWatchlist = async (id: string) => {
    try {
      await deleteAPI(`/api/v1/watchlists/${id}`);
      if (expandedId === id) setExpandedId(null);
      loadWatchlists();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("msg.failed_delete"));
    }
  };

  const handleAddAsset = async (watchlistId: string) => {
    const symbol = addSymbol[watchlistId]?.trim().toUpperCase();
    if (!symbol) return;
    setAdding(watchlistId);
    try {
      await postAPI(`/api/v1/watchlists/${watchlistId}/assets`, {
        symbol,
        name: symbol,
        type: addType[watchlistId] || "stock",
      });
      setAddSymbol((prev) => ({ ...prev, [watchlistId]: "" }));
      loadWatchlists();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("msg.failed_add"));
    } finally {
      setAdding(null);
    }
  };

  const handleRemoveAsset = async (watchlistId: string, symbol: string) => {
    try {
      await deleteAPI(`/api/v1/watchlists/${watchlistId}/assets/${symbol}`);
      loadWatchlists();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("msg.failed_remove"));
    }
  };

  if (loading) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4 animate-pulse">
        <div className="h-4 bg-oracle-border rounded w-24" />
      </div>
    );
  }

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      {/* Collapsible header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-between w-full"
      >
        <div className="flex items-center gap-2">
          <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
            {t("section.watchlists")}
          </h3>
          <span className="text-oracle-muted text-xs">
            {watchlists.length} · {totalAssets} {t("msg.assets")}
          </span>
        </div>
        {collapsed
          ? <ChevronDown className="w-4 h-4 text-oracle-muted" />
          : <ChevronUp className="w-4 h-4 text-oracle-muted" />
        }
      </button>

      {error && (
        <p className="text-oracle-red text-xs mt-2">{error}</p>
      )}

      {/* Collapsible content */}
      {!collapsed && (
        <div className="mt-3">
          {/* Create new watchlist */}
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              placeholder={t("placeholder.new_watchlist")}
              className="flex-1 bg-oracle-bg border border-oracle-border rounded px-3 py-1.5 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent"
            />
            <button
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
              className="bg-oracle-accent text-white text-sm px-3 py-1.5 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
            >
              +
            </button>
          </div>

          {watchlists.length === 0 ? (
            <p className="text-oracle-muted text-sm">{t("msg.no_watchlists")}</p>
          ) : (
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {watchlists.map((wl) => {
                const isExpanded = expandedId === wl.id;
                return (
                  <div
                    key={wl.id}
                    className="bg-oracle-bg rounded border border-oracle-border/50 overflow-hidden"
                  >
                    {/* Watchlist header */}
                    <div className="flex items-center justify-between px-3 py-2">
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : wl.id)}
                        className="flex items-center gap-2 flex-1 text-left"
                      >
                        <span className="text-oracle-muted text-xs transition-transform" style={{
                          display: "inline-block",
                          transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                        }}>
                          &#9654;
                        </span>
                        <span className="text-sm font-medium text-oracle-text">
                          {wl.name}
                        </span>
                        <span className="text-oracle-muted text-xs">
                          {wl.assets.length} {t("msg.assets")}
                        </span>
                      </button>
                      <button
                        onClick={() => handleDeleteWatchlist(wl.id)}
                        className="text-oracle-muted hover:text-oracle-red text-xs transition-colors ml-2"
                        title={t("action.delete_watchlist")}
                      >
                        &#10005;
                      </button>
                    </div>

                    {/* Expanded content */}
                    {isExpanded && (
                      <div className="border-t border-oracle-border/50 px-3 py-2">
                        {/* Add symbol input */}
                        <div className="flex gap-2 mb-2">
                          <SymbolAutocomplete
                            value={addSymbol[wl.id] || ""}
                            onChange={(v) => setAddSymbol((prev) => ({ ...prev, [wl.id]: v }))}
                            onSubmit={() => handleAddAsset(wl.id)}
                            onSelectResult={(r) => setAddType((prev) => ({ ...prev, [wl.id]: r.type }))}
                            placeholder={t("watchlist.add_placeholder")}
                            className="flex-1"
                            size="sm"
                          />
                          <button
                            onClick={() => handleAddAsset(wl.id)}
                            disabled={adding === wl.id || !addSymbol[wl.id]?.trim()}
                            className="bg-oracle-accent text-white text-xs px-2 py-1 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
                          >
                            {adding === wl.id ? "..." : t("action.add")}
                          </button>
                        </div>

                        {/* Asset list */}
                        {wl.assets.length === 0 ? (
                          <p className="text-oracle-muted text-xs py-1">
                            {t("watchlist.empty")}
                          </p>
                        ) : (
                          <div className="space-y-1">
                            {wl.assets.map((asset: Asset) => (
                              <div
                                key={asset.symbol}
                                className="flex items-center justify-between py-1.5 px-1 hover:bg-oracle-panel/50 rounded transition-colors"
                              >
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className="text-sm font-medium text-oracle-text">
                                    {asset.symbol}
                                  </span>
                                  <span className="text-oracle-muted text-xs truncate max-w-[80px]">
                                    {asset.name !== asset.symbol ? asset.name : ""}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Sparkline data={sparklines[asset.symbol] ?? []} width={48} height={18} />
                                  <span className="text-oracle-text text-xs font-mono">
                                    {formatPrice(asset.price)}
                                  </span>
                                  <span
                                    className={`text-xs font-mono w-14 text-right ${
                                      asset.change_percent >= 0
                                        ? "text-oracle-green"
                                        : "text-oracle-red"
                                    }`}
                                  >
                                    {asset.change_percent >= 0 ? "+" : ""}
                                    {asset.change_percent.toFixed(2)}%
                                  </span>
                                  <button
                                    onClick={() => handleRemoveAsset(wl.id, asset.symbol)}
                                    className="text-oracle-muted hover:text-oracle-red text-xs ml-1 transition-colors"
                                    title={`${t("action.remove")} ${asset.symbol}`}
                                  >
                                    &#10005;
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
