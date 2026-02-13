"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { fetchAPI } from "@/lib/api";

interface SearchResult {
  symbol: string;
  name: string;
  type: string;
  match: string;
}

interface SearchResponse {
  results: SearchResult[];
  query: string;
}

interface SymbolAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (symbol: string) => void;
  onSelectResult?: (result: { symbol: string; name: string; type: string }) => void;
  placeholder?: string;
  className?: string;
  size?: "sm" | "md";
}

export default function SymbolAutocomplete({
  value,
  onChange,
  onSubmit,
  onSelectResult,
  placeholder = "Symbol (e.g. AAPL, BTC)",
  className = "",
  size = "md",
}: SymbolAutocompleteProps) {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async (q: string) => {
    if (q.trim().length === 0) {
      setResults([]);
      setOpen(false);
      return;
    }
    try {
      const data = await fetchAPI<SearchResponse>(
        `/api/v1/market/search?q=${encodeURIComponent(q.trim())}&limit=8`
      );
      setResults(data.results);
      setOpen(data.results.length > 0);
      setSelectedIdx(-1);
    } catch {
      setResults([]);
      setOpen(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(value), 150);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [value, search]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const selectResult = (result: SearchResult) => {
    onChange(result.symbol);
    setOpen(false);
    onSelectResult?.({ symbol: result.symbol, name: result.name, type: result.type });
    onSubmit(result.symbol);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) {
      if (e.key === "Enter") {
        e.preventDefault();
        onSubmit(value.trim().toUpperCase());
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((prev) => Math.max(prev - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedIdx >= 0 && selectedIdx < results.length) {
        selectResult(results[selectedIdx]);
      } else {
        onSubmit(value.trim().toUpperCase());
        setOpen(false);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "Tab" && results.length > 0) {
      e.preventDefault();
      const idx = selectedIdx >= 0 ? selectedIdx : 0;
      onChange(results[idx].symbol);
      setOpen(false);
    }
  };

  const typeColors: Record<string, string> = {
    stock: "text-blue-400",
    etf: "text-amber-400",
    crypto: "text-purple-400",
    commodity: "text-orange-400",
  };

  const sizeClasses = size === "sm"
    ? "px-2 py-1 text-xs"
    : "px-3 py-1.5 text-sm";

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => results.length > 0 && setOpen(true)}
        placeholder={placeholder}
        className={`w-full bg-oracle-bg border border-oracle-border rounded ${sizeClasses} text-oracle-text placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent`}
      />

      {open && results.length > 0 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-oracle-panel border border-oracle-border rounded-md shadow-lg max-h-64 overflow-y-auto">
          {results.map((r, i) => (
            <button
              key={r.symbol}
              onClick={() => selectResult(r)}
              onMouseEnter={() => setSelectedIdx(i)}
              className={`w-full flex items-center justify-between px-3 py-2 text-left transition-colors ${
                i === selectedIdx
                  ? "bg-oracle-accent/20 text-oracle-text"
                  : "text-oracle-text hover:bg-oracle-bg"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-medium text-sm">{r.symbol}</span>
                <span className="text-oracle-muted text-xs truncate">{r.name}</span>
              </div>
              <span className={`text-[10px] font-medium uppercase ${typeColors[r.type] || "text-oracle-muted"}`}>
                {r.type}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
