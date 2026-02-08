"use client";

import { useEffect, useState } from "react";
import { fetchAPI, postAPI, deleteAPI } from "@/lib/api";
import type { WatchlistList, Watchlist } from "@/types";

export default function WatchlistCard() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const loadWatchlists = () => {
    fetchAPI<WatchlistList>("/api/v1/watchlists/")
      .then((data) => setWatchlists(data.watchlists))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadWatchlists();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await postAPI<Watchlist>("/api/v1/watchlists/", { name: newName.trim() });
      setNewName("");
      loadWatchlists();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAPI(`/api/v1/watchlists/${id}`);
      loadWatchlists();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  if (loading) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6 animate-pulse">
        <div className="h-4 bg-oracle-border rounded w-24 mb-3" />
        <div className="h-6 bg-oracle-border rounded w-full" />
      </div>
    );
  }

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium mb-3 uppercase tracking-wide">
        Watchlists
      </h3>

      {error && (
        <p className="text-oracle-red text-xs mb-2">{error}</p>
      )}

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          placeholder="New watchlist name..."
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
        <p className="text-oracle-muted text-sm">No watchlists yet.</p>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {watchlists.map((wl) => (
            <div
              key={wl.id}
              className="flex items-center justify-between bg-oracle-bg rounded px-3 py-2"
            >
              <div>
                <span className="text-sm font-medium text-white">
                  {wl.name}
                </span>
                <span className="text-oracle-muted text-xs ml-2">
                  {wl.assets.length} asset{wl.assets.length !== 1 ? "s" : ""}
                </span>
              </div>
              <button
                onClick={() => handleDelete(wl.id)}
                className="text-oracle-muted hover:text-oracle-red text-xs transition-colors"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
