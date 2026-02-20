"use client";

import { useState, useEffect, useRef } from "react";
import { useView, type View } from "@/contexts/ViewContext";

interface CommandItem {
  id: string;
  label: string;
  category: string;
  action: () => void;
}

export default function CommandBar() {
  const { commandBarOpen, setCommandBarOpen, setActiveView, setSelectedSymbol } =
    useView();
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: CommandItem[] = [
    { id: "v-overview", label: "Go to Overview", category: "Views", action: () => setActiveView("overview") },
    { id: "v-analysis", label: "Go to Analysis", category: "Views", action: () => setActiveView("analysis") },
    { id: "v-screener", label: "Go to Screener", category: "Views", action: () => setActiveView("screener") },
    { id: "v-movers", label: "Go to Movers", category: "Views", action: () => setActiveView("movers") },
    { id: "v-volatility", label: "Go to Volatility", category: "Views", action: () => setActiveView("volatility") },
    { id: "v-paper", label: "Go to Paper Trade", category: "Views", action: () => setActiveView("paper-trade") },
    { id: "v-rl", label: "Go to AI Trading", category: "Views", action: () => setActiveView("rl-trading") },
    { id: "v-alerts", label: "Go to Alerts", category: "Views", action: () => setActiveView("alerts") },
    { id: "v-chat", label: "Go to Chat", category: "Views", action: () => setActiveView("chat") },
    { id: "v-commodities", label: "Go to Commodities", category: "Views", action: () => setActiveView("commodities") },
    { id: "v-macro", label: "Go to Macro", category: "Views", action: () => setActiveView("macro") },
    { id: "v-prediction", label: "Go to Prediction", category: "Views", action: () => setActiveView("prediction") },
  ];

  // If query looks like a ticker symbol, add a "Look up" action
  const isSymbolQuery = /^[A-Za-z]{1,5}$/.test(query.trim());
  const allCommands = isSymbolQuery
    ? [
        {
          id: "lookup",
          label: `Look up ${query.trim().toUpperCase()}`,
          category: "Symbol",
          action: () => {
            setSelectedSymbol(query.trim().toUpperCase());
            setActiveView("overview");
          },
        },
        ...commands,
      ]
    : commands;

  const filtered = allCommands.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (commandBarOpen) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [commandBarOpen]);

  const execute = (cmd: CommandItem) => {
    cmd.action();
    setCommandBarOpen(false);
  };

  if (!commandBarOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
      onClick={() => setCommandBarOpen(false)}
    >
      <div className="fixed inset-0 bg-black/60" />
      <div
        className="relative w-full max-w-lg bg-oracle-panel border border-oracle-border rounded-lg shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") setCommandBarOpen(false);
            if (e.key === "Enter" && filtered.length > 0) execute(filtered[0]);
          }}
          placeholder="Type a command or symbol..."
          className="w-full bg-transparent px-4 py-3 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none border-b border-oracle-border"
        />
        <div className="max-h-64 overflow-y-auto py-2">
          {filtered.length === 0 && (
            <p className="px-4 py-2 text-oracle-muted text-sm">No results</p>
          )}
          {filtered.map((cmd) => (
            <button
              key={cmd.id}
              onClick={() => execute(cmd)}
              className="w-full flex items-center justify-between px-4 py-2 text-sm text-oracle-text hover:bg-oracle-bg transition-colors text-left"
            >
              <span>{cmd.label}</span>
              <span className="text-oracle-muted text-xs">{cmd.category}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
