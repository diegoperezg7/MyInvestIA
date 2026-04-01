"use client";

import { useState, useEffect } from "react";
import { fetchAPI } from "@/lib/api";
import type { EconomicCalendarResponse, EconomicEvent } from "@/types";

const IMPACT_STYLES: Record<string, string> = {
  high: "bg-red-500/15 text-red-400 border-red-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  low: "bg-green-500/15 text-green-400 border-green-500/30",
};

function ImpactBadge({ impact }: { impact: string }) {
  const style = IMPACT_STYLES[impact] || IMPACT_STYLES.low;
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${style}`}>
      {impact.toUpperCase()}
    </span>
  );
}

function formatNum(val: number | null): string {
  if (val === null || val === undefined) return "-";
  if (Math.abs(val) >= 1e9) return `${(val / 1e9).toFixed(1)}B`;
  if (Math.abs(val) >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
  return val.toFixed(2);
}

type DateRange = "this_week" | "next_week" | "this_month";

function getDateRange(range: DateRange): { start: string; end: string } {
  const now = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  const fmt = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  if (range === "this_week") {
    const day = now.getDay();
    const start = new Date(now);
    start.setDate(now.getDate() - day + 1); // Monday
    const end = new Date(start);
    end.setDate(start.getDate() + 4); // Friday
    return { start: fmt(start), end: fmt(end) };
  }
  if (range === "next_week") {
    const day = now.getDay();
    const start = new Date(now);
    start.setDate(now.getDate() - day + 8); // Next Monday
    const end = new Date(start);
    end.setDate(start.getDate() + 4);
    return { start: fmt(start), end: fmt(end) };
  }
  // this_month
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { start: fmt(start), end: fmt(end) };
}

export default function EconomicCalendar() {
  const [data, setData] = useState<EconomicCalendarResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>("this_week");
  const [tab, setTab] = useState<"events" | "earnings">("events");
  const [impactFilter, setImpactFilter] = useState<string>("all");

  const fetchData = async (range: DateRange) => {
    setLoading(true);
    setError(null);
    const { start, end } = getDateRange(range);
    try {
      const result = await fetchAPI<EconomicCalendarResponse>(
        `/api/v1/market/calendar?start_date=${start}&end_date=${end}`,
        { skipCache: true }
      );
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load calendar");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(dateRange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  const filteredEvents = data?.events.filter(
    (e) => impactFilter === "all" || e.impact === impactFilter
  ) ?? [];

  const today = new Date().toISOString().split("T")[0];

  // Group events by date
  const groupedEvents = filteredEvents.reduce<Record<string, EconomicEvent[]>>((acc, event) => {
    const date = event.date || "Unknown";
    if (!acc[date]) acc[date] = [];
    acc[date].push(event);
    return acc;
  }, {});

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          Economic Calendar
        </h3>
        <div className="flex gap-1">
          {(["this_week", "next_week", "this_month"] as DateRange[]).map((r) => (
            <button
              key={r}
              onClick={() => setDateRange(r)}
              className={`text-[10px] px-2 py-0.5 rounded transition-colors ${
                dateRange === r
                  ? "bg-oracle-accent text-white"
                  : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
              }`}
            >
              {r === "this_week" ? "This Week" : r === "next_week" ? "Next Week" : "Month"}
            </button>
          ))}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-3">
        <button
          onClick={() => setTab("events")}
          className={`text-xs px-3 py-1 rounded transition-colors ${
            tab === "events"
              ? "bg-oracle-accent text-white"
              : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
          }`}
        >
          Events ({data?.events.length ?? 0})
        </button>
        <button
          onClick={() => setTab("earnings")}
          className={`text-xs px-3 py-1 rounded transition-colors ${
            tab === "earnings"
              ? "bg-oracle-accent text-white"
              : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
          }`}
        >
          Earnings ({data?.earnings.length ?? 0})
        </button>
        {tab === "events" && (
          <div className="flex gap-1 ml-auto">
            {["all", "high", "medium", "low"].map((level) => (
              <button
                key={level}
                onClick={() => setImpactFilter(level)}
                className={`text-[10px] px-1.5 py-0.5 rounded transition-colors ${
                  impactFilter === level
                    ? "bg-oracle-accent/20 text-oracle-accent"
                    : "text-oracle-muted hover:text-oracle-text"
                }`}
              >
                {level === "all" ? "All" : level.charAt(0).toUpperCase() + level.slice(1)}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <p className="text-oracle-red text-sm mb-2">{error}</p>}

      {loading && (
        <div className="animate-pulse space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-6 bg-oracle-bg rounded" />
          ))}
        </div>
      )}

      {!loading && tab === "events" && (
        <div className="max-h-[500px] overflow-y-auto space-y-3">
          {Object.entries(groupedEvents).map(([date, events]) => (
            <div key={date}>
              <div className={`text-xs font-medium px-2 py-1 rounded mb-1 ${
                date === today
                  ? "bg-oracle-accent/10 text-oracle-accent"
                  : "text-oracle-muted"
              }`}>
                {new Date(date + "T00:00:00").toLocaleDateString("en-US", {
                  weekday: "short", month: "short", day: "numeric",
                })}
                {date === today && " (Today)"}
              </div>
              <table className="w-full text-xs">
                <tbody>
                  {events.map((event, i) => (
                    <tr
                      key={`${date}-${i}`}
                      className="border-t border-oracle-border/30 hover:bg-oracle-bg/50"
                    >
                      <td className="py-1.5 pr-2 text-oracle-muted w-12">{event.time || "-"}</td>
                      <td className="py-1.5 pr-2 text-oracle-text flex-1">{event.event}</td>
                      <td className="py-1.5 pr-2 text-oracle-muted w-8">{event.country}</td>
                      <td className="py-1.5 pr-2 w-16"><ImpactBadge impact={event.impact} /></td>
                      <td className="py-1.5 pr-2 text-oracle-muted font-mono w-14 text-right">
                        {formatNum(event.forecast)}
                      </td>
                      <td className="py-1.5 pr-2 text-oracle-muted font-mono w-14 text-right">
                        {formatNum(event.previous)}
                      </td>
                      <td className="py-1.5 font-mono w-14 text-right">
                        {event.actual !== null ? (
                          <span className="text-oracle-text font-medium">{formatNum(event.actual)}</span>
                        ) : (
                          <span className="text-oracle-muted">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          {filteredEvents.length === 0 && (
            <p className="text-oracle-muted text-sm text-center py-4">
              No events found for this period
            </p>
          )}
        </div>
      )}

      {!loading && tab === "earnings" && (
        <div className="max-h-[500px] overflow-y-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-oracle-muted text-left border-b border-oracle-border">
                <th className="pb-1.5 pr-2">Date</th>
                <th className="pb-1.5 pr-2">Symbol</th>
                <th className="pb-1.5 pr-2 text-right">EPS Est.</th>
                <th className="pb-1.5 pr-2 text-right">EPS Act.</th>
                <th className="pb-1.5 pr-2 text-right">Rev Est.</th>
                <th className="pb-1.5 text-right">Rev Act.</th>
              </tr>
            </thead>
            <tbody>
              {(data?.earnings ?? []).map((e, i) => (
                <tr key={`${e.symbol}-${i}`} className="border-t border-oracle-border/30 hover:bg-oracle-bg/50">
                  <td className="py-1.5 pr-2 text-oracle-muted">
                    {new Date(e.date + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </td>
                  <td className="py-1.5 pr-2 text-oracle-text font-medium">{e.symbol}</td>
                  <td className="py-1.5 pr-2 text-oracle-muted font-mono text-right">{formatNum(e.eps_estimate)}</td>
                  <td className="py-1.5 pr-2 font-mono text-right">
                    {e.eps_actual !== null ? (
                      <span className={
                        e.eps_actual > (e.eps_estimate ?? 0) ? "text-oracle-green" : "text-oracle-red"
                      }>
                        {formatNum(e.eps_actual)}
                      </span>
                    ) : "-"}
                  </td>
                  <td className="py-1.5 pr-2 text-oracle-muted font-mono text-right">{formatNum(e.revenue_estimate)}</td>
                  <td className="py-1.5 font-mono text-right">
                    {e.revenue_actual !== null ? (
                      <span className={
                        e.revenue_actual > (e.revenue_estimate ?? 0) ? "text-oracle-green" : "text-oracle-red"
                      }>
                        {formatNum(e.revenue_actual)}
                      </span>
                    ) : "-"}
                  </td>
                </tr>
              ))}
              {(data?.earnings ?? []).length === 0 && (
                <tr>
                  <td colSpan={6} className="text-oracle-muted text-center py-4">
                    No earnings reports found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
