"use client";

import { useState, useEffect } from "react";
import { fetchAPI } from "@/lib/api";
import Sparkline from "@/components/ui/Sparkline";
import useSparklines from "@/hooks/useSparklines";
import type { MacroIntelligenceResponse, MacroIndicatorDetail } from "@/types";

const TREND_ICONS: Record<string, string> = {
  up: "\u25B2",
  down: "\u25BC",
  stable: "\u25C6",
};

const TREND_COLORS: Record<string, string> = {
  up: "text-oracle-green",
  down: "text-oracle-red",
  stable: "text-oracle-muted",
};

const RISK_COLORS: Record<string, string> = {
  low: "text-oracle-green",
  moderate: "text-oracle-accent",
  elevated: "text-oracle-yellow",
  high: "text-oracle-red",
};

function IndicatorRow({ indicator, sparkData }: { indicator: MacroIndicatorDetail; sparkData: number[] }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-oracle-border last:border-b-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm text-oracle-text font-medium truncate">
          {indicator.name}
        </p>
        <p className="text-xs text-oracle-muted truncate mt-0.5">
          {indicator.impact_description}
        </p>
      </div>
      <div className="flex items-center gap-3 ml-4 shrink-0">
        <Sparkline data={sparkData} width={56} height={22} />
        <span className="text-sm text-oracle-text font-mono">
          {indicator.value.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </span>
        <span
          className={`text-xs font-medium ${TREND_COLORS[indicator.trend]}`}
        >
          {TREND_ICONS[indicator.trend]}{" "}
          {indicator.change_percent > 0 ? "+" : ""}
          {indicator.change_percent.toFixed(2)}%
        </span>
      </div>
    </div>
  );
}

export default function MacroPanel() {
  const [data, setData] = useState<MacroIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const tickers = data?.indicators.map((i) => i.ticker).filter(Boolean) ?? [];
  const sparklines = useSparklines(tickers);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetchAPI<MacroIntelligenceResponse>(
          "/api/v1/market/macro"
        );
        if (!cancelled) {
          setData(res);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load macro data");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide mb-3">
        Macro Intelligence
      </h3>

      {loading && (
        <p className="text-oracle-muted text-sm">Loading macro data...</p>
      )}

      {error && <p className="text-oracle-red text-sm">{error}</p>}

      {data && (
        <>
          {/* Summary banner */}
          <div className="bg-oracle-bg/50 rounded-lg px-4 py-3 mb-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-oracle-muted uppercase">
                Environment
              </span>
              <span className="text-xs text-oracle-muted uppercase">
                Risk Level
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-oracle-text capitalize">
                {data.summary.environment}
              </span>
              <span
                className={`text-sm font-medium capitalize ${
                  RISK_COLORS[data.summary.risk_level] || "text-oracle-muted"
                }`}
              >
                {data.summary.risk_level}
              </span>
            </div>
            {data.summary.key_signals.length > 0 && (
              <div className="mt-2 space-y-1">
                {data.summary.key_signals.map((signal, i) => (
                  <p key={i} className="text-xs text-oracle-text">
                    {signal}
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* Indicator list */}
          <div className="space-y-0">
            {data.indicators.map((indicator) => (
              <IndicatorRow
                key={indicator.name}
                indicator={indicator}
                sparkData={sparklines[indicator.ticker] ?? []}
              />
            ))}
          </div>

          {data.indicators.length === 0 && (
            <p className="text-oracle-muted text-sm">
              No macro data available.
            </p>
          )}
        </>
      )}
    </div>
  );
}
