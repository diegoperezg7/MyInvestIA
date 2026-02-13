"use client";

import { useView, type View } from "@/contexts/ViewContext";

const VIEWS: { key: View; label: string; shortcut: string }[] = [
  { key: "overview", label: "OVERVIEW", shortcut: "1" },
  { key: "analysis", label: "ANALYSIS", shortcut: "2" },
  { key: "screener", label: "SCREENER", shortcut: "3" },
  { key: "movers", label: "MOVERS", shortcut: "4" },
  { key: "volatility", label: "VOLATILITY", shortcut: "5" },
  { key: "paper-trade", label: "PAPER TRADE", shortcut: "6" },
  { key: "alerts", label: "ALERTS", shortcut: "7" },
  { key: "chat", label: "CHAT", shortcut: "8" },
  { key: "macro", label: "MACRO", shortcut: "9" },
];

export default function ViewSwitcher() {
  const { activeView, setActiveView, setCommandBarOpen } = useView();

  return (
    <nav className="flex items-center gap-1 bg-oracle-panel border-b border-oracle-border px-4 py-2">
      <span className="font-bold text-sm mr-4 tracking-wider" style={{ color: "var(--oracle-primary)" }}>
        MyInvestIA
      </span>

      {VIEWS.map((v) => (
        <button
          key={v.key}
          onClick={() => setActiveView(v.key)}
          className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
            activeView === v.key
              ? "bg-oracle-accent text-oracle-text"
              : "text-oracle-muted hover:text-oracle-text hover:bg-oracle-bg"
          }`}
        >
          {v.label}
          <span className="ml-1.5 text-[10px] opacity-50">{v.shortcut}</span>
        </button>
      ))}

      <div className="ml-auto flex items-center gap-2">
        <button
          onClick={() => setCommandBarOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-oracle-muted bg-oracle-bg border border-oracle-border rounded hover:border-oracle-accent transition-colors"
        >
          <span>Search</span>
          <kbd className="text-[10px] bg-oracle-panel px-1 rounded">{"\u2318"}K</kbd>
        </button>
      </div>
    </nav>
  );
}
