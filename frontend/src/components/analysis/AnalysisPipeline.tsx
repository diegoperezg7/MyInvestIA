"use client";

import { useState } from "react";
import { useAnalysisPipeline } from "@/hooks/useAnalysisPipeline";
import ReactMarkdown from "react-markdown";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";

const STEP_ICONS: Record<string, string> = {
  pending: "○",
  running: "◎",
  completed: "●",
  failed: "✕",
  skipped: "◌",
};

export default function AnalysisPipeline() {
  const [symbol, setSymbol] = useState("");
  const { status, loading, error, run, cancel } = useAnalysisPipeline();

  const handleRun = () => {
    if (symbol.trim()) run(symbol.trim().toUpperCase());
  };

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide mb-3">
        Deep Analysis Pipeline
      </h3>

      <div className="flex gap-2 mb-4">
        <SymbolAutocomplete
          value={symbol}
          onChange={setSymbol}
          onSubmit={(s) => { setSymbol(s); if (s.trim()) run(s.trim().toUpperCase()); }}
          placeholder="Symbol (e.g. AAPL)"
          className="flex-1"
        />
        {loading ? (
          <button
            onClick={cancel}
            className="bg-oracle-red text-white text-sm px-4 py-1.5 rounded hover:bg-oracle-red/80 transition-colors"
          >
            Cancel
          </button>
        ) : (
          <button
            onClick={handleRun}
            disabled={!symbol.trim()}
            className="bg-oracle-accent text-white text-sm px-4 py-1.5 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
          >
            Analyze
          </button>
        )}
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {status && (
        <div>
          {/* Progress steps */}
          <div className="space-y-2 mb-4">
            {status.steps.map((step) => (
              <div key={step.id} className="flex items-center gap-3">
                <span
                  className={`text-sm ${
                    step.status === "completed"
                      ? "text-oracle-green"
                      : step.status === "running"
                      ? "text-oracle-accent animate-pulse"
                      : step.status === "failed"
                      ? "text-oracle-red"
                      : step.status === "skipped"
                      ? "text-oracle-muted"
                      : "text-oracle-border"
                  }`}
                >
                  {STEP_ICONS[step.status]}
                </span>
                <div className="flex-1">
                  <span className="text-sm text-oracle-text">{step.name}</span>
                  {step.status === "running" && (
                    <span className="text-xs text-oracle-muted ml-2">
                      {step.description}
                    </span>
                  )}
                  {step.duration_ms !== null && step.status !== "running" && (
                    <span className="text-xs text-oracle-muted ml-2">
                      {step.duration_ms}ms
                    </span>
                  )}
                </div>
                {step.result && step.status === "completed" && (
                  <span className="text-xs text-oracle-muted">
                    {Object.entries(step.result)
                      .slice(0, 2)
                      .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
                      .join(", ")}
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Progress bar */}
          <div className="h-1 bg-oracle-border rounded-full mb-4 overflow-hidden">
            <div
              className="h-full bg-oracle-accent transition-all duration-500"
              style={{
                width: `${(status.current_step / status.total_steps) * 100}%`,
              }}
            />
          </div>

          {/* Final result */}
          {status.completed && status.final_analysis && (
            <div className="bg-oracle-bg rounded-lg p-4 border border-oracle-border">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-oracle-text font-bold">{status.symbol}</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded border ${
                    status.signal.includes("buy") || status.signal === "bullish"
                      ? "bg-oracle-green/10 text-oracle-green border-oracle-green/30"
                      : status.signal.includes("sell") || status.signal === "bearish"
                      ? "bg-oracle-red/10 text-oracle-red border-oracle-red/30"
                      : "bg-oracle-yellow/10 text-oracle-yellow border-oracle-yellow/30"
                  }`}
                >
                  {status.signal.toUpperCase()}
                </span>
                <span className="text-oracle-muted text-xs">
                  {(status.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              <div className="prose prose-invert prose-sm max-w-none text-oracle-text">
                <ReactMarkdown>{status.final_analysis}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
