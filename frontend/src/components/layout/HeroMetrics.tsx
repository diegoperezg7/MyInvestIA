"use client";

import { useEffect, useMemo, useState } from "react";
import { useView, type View } from "@/contexts/ViewContext";
import { fetchAPI } from "@/lib/api";
import useLanguageStore from "@/stores/useLanguageStore";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useSparklines from "@/hooks/useSparklines";
import type { Portfolio, PortfolioHolding, MacroIntelligenceResponse } from "@/types";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

const MARKET_OPEN_MIN = 570;  // 9:30 AM ET
const MARKET_CLOSE_MIN = 960; // 4:00 PM ET

function getEasternNow(): Date {
  return new Date(new Date().toLocaleString("en-US", { timeZone: "America/New_York" }));
}

function isMarketOpen(): boolean {
  const eastern = getEasternNow();
  const day = eastern.getDay();
  const time = eastern.getHours() * 60 + eastern.getMinutes();
  return day >= 1 && day <= 5 && time >= MARKET_OPEN_MIN && time < MARKET_CLOSE_MIN;
}

/** Returns seconds until next market close (if open) or next market open (if closed). */
function getMarketCountdown(): { secondsLeft: number; isOpen: boolean } {
  const eastern = getEasternNow();
  const day = eastern.getDay();
  const nowMin = eastern.getHours() * 60 + eastern.getMinutes();
  const nowSec = eastern.getSeconds();
  const open = day >= 1 && day <= 5 && nowMin >= MARKET_OPEN_MIN && nowMin < MARKET_CLOSE_MIN;

  if (open) {
    // seconds until 4:00 PM ET
    return { secondsLeft: (MARKET_CLOSE_MIN - nowMin) * 60 - nowSec, isOpen: true };
  }

  // Calculate seconds until next open
  let daysUntilOpen = 0;
  if (day === 0) daysUntilOpen = 1;                          // Sunday → Monday
  else if (day === 6) daysUntilOpen = 2;                     // Saturday → Monday
  else if (nowMin >= MARKET_CLOSE_MIN) daysUntilOpen = day === 5 ? 3 : 1; // After close → next trading day
  // else: before open today, daysUntilOpen = 0

  const secsToday = (MARKET_OPEN_MIN - nowMin) * 60 - nowSec;
  const secondsLeft = daysUntilOpen > 0
    ? (daysUntilOpen - 1) * 86400 + (24 * 60 - nowMin) * 60 - nowSec + MARKET_OPEN_MIN * 60
    : secsToday;

  return { secondsLeft: Math.max(0, secondsLeft), isOpen: false };
}

function formatCountdown(totalSec: number): string {
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h ${m.toString().padStart(2, "0")}m ${s.toString().padStart(2, "0")}s`;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

/** Map VIX to 0-100 sentiment score (0 = very bearish, 100 = very bullish) */
function vixToScore(vix: number): number {
  const clamped = Math.max(10, Math.min(45, vix));
  return Math.round(((45 - clamped) / 35) * 100);
}

function getSentimentLabel(score: number, t: (k: string) => string): { label: string; color: string } {
  if (score >= 75) return { label: t("hero.very_bullish"), color: "text-oracle-green" };
  if (score >= 55) return { label: t("hero.bullish"), color: "text-oracle-green" };
  if (score >= 40) return { label: t("hero.neutral"), color: "text-oracle-yellow" };
  if (score >= 20) return { label: t("hero.bearish"), color: "text-oracle-red" };
  return { label: t("hero.very_bearish"), color: "text-oracle-red" };
}

function SentimentGauge({ score }: { score: number }) {
  // score: 0 (bearish) to 100 (bullish)
  // Needle angle: -90° (left/bearish) to +90° (right/bullish)
  const angle = -90 + (score / 100) * 180;
  const needleColor =
    score >= 55 ? "var(--color-oracle-green)" :
    score >= 40 ? "var(--color-oracle-yellow)" :
    "var(--color-oracle-red)";

  return (
    <svg viewBox="0 0 120 70" className="w-full max-w-[100px] mx-auto">
      {/* Background arc segments */}
      {/* Red (bearish) zone: left third */}
      <path
        d="M 10 60 A 50 50 0 0 1 40 14.5"
        fill="none"
        stroke="var(--color-oracle-red)"
        strokeWidth="6"
        strokeLinecap="round"
        opacity="0.25"
      />
      {/* Yellow (neutral) zone: center third */}
      <path
        d="M 42 13.5 A 50 50 0 0 1 78 13.5"
        fill="none"
        stroke="var(--color-oracle-yellow)"
        strokeWidth="6"
        strokeLinecap="round"
        opacity="0.25"
      />
      {/* Green (bullish) zone: right third */}
      <path
        d="M 80 14.5 A 50 50 0 0 1 110 60"
        fill="none"
        stroke="var(--color-oracle-green)"
        strokeWidth="6"
        strokeLinecap="round"
        opacity="0.25"
      />
      {/* Needle */}
      <g transform={`rotate(${angle}, 60, 60)`}>
        <line
          x1="60" y1="60" x2="60" y2="18"
          stroke={needleColor}
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <circle cx="60" cy="60" r="3.5" fill={needleColor} />
      </g>
      {/* Center dot */}
      <circle cx="60" cy="60" r="2" fill="var(--color-oracle-panel)" />
    </svg>
  );
}

/** Mini area chart rendered as card background */
function MiniPortfolioChart({ sparklines, holdings }: {
  sparklines: Record<string, number[]>;
  holdings: PortfolioHolding[];
}) {
  const maxLen = Math.max(...holdings.map((h) => (sparklines[h.asset.symbol] ?? []).length), 0);
  if (maxLen < 2) return null;

  const chartData: { i: number; value: number }[] = [];
  for (let i = 0; i < maxLen; i++) {
    let total = 0;
    for (const h of holdings) {
      const prices = sparklines[h.asset.symbol] ?? [];
      const price = prices[i] ?? prices[prices.length - 1] ?? 0;
      total += price * h.quantity;
    }
    chartData.push({ i, value: total });
  }

  const first = chartData[0].value;
  const last = chartData[chartData.length - 1].value;
  const color = last >= first ? "#10b981" : "#ef4444";

  return (
    <div className="absolute bottom-0 left-0 right-0 h-[48px] opacity-20 pointer-events-none">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="heroPortfolioGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.8} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill="url(#heroPortfolioGrad)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Horizontal P&L contribution bar + top contributors */
function PnlContributionBar({ holdings }: { holdings: PortfolioHolding[] }) {
  if (holdings.length === 0) return null;

  const contributions = holdings.map((h) => {
    const cp = h.asset.change_percent;
    const dailyPnl = h.current_value * cp / (100 + cp);
    return { symbol: h.asset.symbol, pnl: dailyPnl };
  });

  const totalAbsPnl = contributions.reduce((s, c) => s + Math.abs(c.pnl), 0);
  if (totalAbsPnl === 0) return null;

  // Sort by absolute contribution for top contributors
  const sorted = [...contributions].sort((a, b) => Math.abs(b.pnl) - Math.abs(a.pnl));
  const top = sorted.slice(0, 3);

  return (
    <div className="mt-2">
      <div className="flex h-1.5 rounded-full overflow-hidden bg-oracle-bg">
        {contributions.map((c) => {
          const pct = (Math.abs(c.pnl) / totalAbsPnl) * 100;
          if (pct < 0.5) return null;
          return (
            <div
              key={c.symbol}
              className="h-full transition-all"
              style={{
                width: `${pct}%`,
                backgroundColor: c.pnl >= 0 ? "#10b981" : "#ef4444",
                opacity: 0.7,
              }}
              title={`${c.symbol}: ${c.pnl >= 0 ? "+" : ""}${c.pnl.toFixed(2)}`}
            />
          );
        })}
      </div>
      <div className="flex gap-2 mt-1.5">
        {top.map((c) => (
          <span key={c.symbol} className="text-[10px] font-mono">
            <span className="text-oracle-muted">{c.symbol}</span>{" "}
            <span className={c.pnl >= 0 ? "text-oracle-green" : "text-oracle-red"}>
              {c.pnl >= 0 ? "+" : ""}{c.pnl.toFixed(1)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

/** Get progress ratio [0, 1] through trading day and the color for that point */
function useTradingDayProgress(): { pct: number; isOpen: boolean; color: string; glowColor: string } {
  const eastern = getEasternNow();
  const nowMin = eastern.getHours() * 60 + eastern.getMinutes();
  const totalTradingMin = MARKET_CLOSE_MIN - MARKET_OPEN_MIN; // 390 min
  const day = eastern.getDay();
  const open = day >= 1 && day <= 5 && nowMin >= MARKET_OPEN_MIN && nowMin < MARKET_CLOSE_MIN;
  const elapsed = Math.max(0, Math.min(totalTradingMin, nowMin - MARKET_OPEN_MIN));
  const ratio = open ? elapsed / totalTradingMin : 0;

  // Green (#10b981) at 0% → Yellow (#eab308) at 60% → Orange (#f97316) at 100%
  const r = ratio <= 0.6
    ? Math.round(16 + (234 - 16) * (ratio / 0.6))
    : Math.round(234 + (249 - 234) * ((ratio - 0.6) / 0.4));
  const g = ratio <= 0.6
    ? Math.round(185 + (179 - 185) * (ratio / 0.6))
    : Math.round(179 + (115 - 179) * ((ratio - 0.6) / 0.4));
  const b = ratio <= 0.6
    ? Math.round(129 + (8 - 129) * (ratio / 0.6))
    : Math.round(8 + (22 - 8) * ((ratio - 0.6) / 0.4));

  const color = open ? `rgb(${r}, ${g}, ${b})` : "rgb(100, 116, 139)";
  const glowColor = open ? `rgba(${r}, ${g}, ${b}, 0.4)` : "transparent";

  return { pct: ratio * 100, isOpen: open, color, glowColor };
}

/** Convert ET minutes-since-midnight to local time string (HH:MM) */
function etMinToLocal(etMin: number): string {
  // Build a Date object for today at etMin in ET, then format in local tz
  const now = new Date();
  const etDateStr = now.toLocaleDateString("en-US", { timeZone: "America/New_York" });
  const base = new Date(etDateStr);
  base.setHours(Math.floor(etMin / 60), etMin % 60, 0, 0);
  // base is in local tz interpreted as ET date — offset to real ET
  const eastern = new Date(base.toLocaleString("en-US", { timeZone: "America/New_York" }));
  const diffMs = base.getTime() - eastern.getTime();
  const local = new Date(base.getTime() + diffMs);
  return local.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

function MarketStatusCard({
  marketOpen,
  countdownText,
  t,
}: {
  marketOpen: boolean;
  countdownText: string;
  t: (k: string) => string;
}) {
  const { pct, color } = useTradingDayProgress();

  const localOpen = etMinToLocal(MARKET_OPEN_MIN);
  const localClose = etMinToLocal(MARKET_CLOSE_MIN);

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-xl overflow-hidden shadow-sm transition-all duration-300 hover:border-oracle-border-hover hover:shadow-md relative">
      {/* Top accent — fills left-to-right with day color when open */}
      <div className="h-[2px] bg-oracle-bg relative">
        <div
          className="absolute inset-y-0 left-0 transition-all duration-1000"
          style={{
            width: marketOpen ? `${pct}%` : "0%",
            backgroundColor: marketOpen ? color : "transparent",
          }}
        />
      </div>

      <div className="p-3 sm:p-5 pb-3 sm:pb-4">
        <p className="text-oracle-muted text-[10px] sm:text-xs font-semibold uppercase tracking-wide mb-1">
          {t("hero.market_status")}
        </p>

        {marketOpen ? (
          <>
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2 sm:h-2.5 sm:w-2.5 shrink-0">
                <span
                  className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                  style={{ backgroundColor: color }}
                />
                <span
                  className="relative inline-flex rounded-full h-2 w-2 sm:h-2.5 sm:w-2.5"
                  style={{ backgroundColor: color }}
                />
              </span>
              <p
                className="text-base sm:text-xl font-bold font-mono transition-colors duration-1000"
                style={{ color }}
              >
                {t("hero.open")}
              </p>
            </div>
            <p className="text-oracle-muted text-[10px] sm:text-xs mt-1 hidden sm:block">{t("hero.us_markets")}</p>
            <p
              className="font-mono text-xs sm:text-sm font-bold mt-1.5 sm:mt-2 transition-colors duration-1000"
              style={{ color }}
            >
              {countdownText}
            </p>
          </>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2 sm:h-2.5 sm:w-2.5 shrink-0">
                <span className="relative inline-flex rounded-full h-2 w-2 sm:h-2.5 sm:w-2.5 bg-oracle-muted/40 animate-pulse" />
              </span>
              <p className="text-base sm:text-xl font-bold font-mono text-oracle-muted/60">
                {t("hero.closed")}
              </p>
            </div>
            <p className="text-oracle-muted text-[10px] sm:text-xs mt-1 hidden sm:block">{t("hero.us_markets")}</p>
            <p className="font-mono text-xs sm:text-sm font-bold mt-1.5 sm:mt-2 text-oracle-muted/80 animate-pulse">
              {countdownText}
            </p>
          </>
        )}

        {/* Trading session progress bar — always visible */}
        <div className="mt-2 sm:mt-3">
          <div className="relative h-1.5 sm:h-2 rounded-full bg-oracle-bg overflow-hidden">
            {marketOpen && (
              <div
                className="absolute inset-y-0 left-0 rounded-full transition-all duration-1000"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            )}
          </div>
          <div className="flex justify-between mt-1 sm:mt-1.5">
            <span className="text-[8px] sm:text-[10px] font-mono text-oracle-muted leading-none">
              {localOpen} <span className="text-oracle-muted/50 hidden sm:inline">({t("hero.et_open")})</span>
            </span>
            <span className="text-[8px] sm:text-[10px] font-mono text-oracle-muted leading-none">
              {localClose} <span className="text-oracle-muted/50 hidden sm:inline">({t("hero.et_close")})</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function OverviewHero() {
  const { t } = useLanguageStore();
  const { formatPrice } = useCurrencyStore();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [macro, setMacro] = useState<MacroIntelligenceResponse | null>(null);
  const [countdown, setCountdown] = useState(getMarketCountdown);

  useEffect(() => {
    fetchAPI<Portfolio>("/api/v1/portfolio/").then(setPortfolio).catch(() => {});
    fetchAPI<MacroIntelligenceResponse>("/api/v1/market/macro").then(setMacro).catch(() => {});
  }, []);

  // Tick countdown every second
  useEffect(() => {
    const interval = setInterval(() => setCountdown(getMarketCountdown()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Sparklines for portfolio holdings
  const holdingSymbols = useMemo(
    () => portfolio?.holdings.map((h) => h.asset.symbol) ?? [],
    [portfolio]
  );
  const sparklines = useSparklines(holdingSymbols);

  const marketOpen = countdown.isOpen;
  const pnlPositive = (portfolio?.daily_pnl ?? 0) >= 0;

  // Extract VIX for sentiment gauge
  const vixIndicator = macro?.indicators.find((i) => i.ticker === "^VIX");
  const vixValue = vixIndicator?.value ?? null;
  const sentimentScore = vixValue !== null ? vixToScore(vixValue) : null;
  const sentiment = sentimentScore !== null ? getSentimentLabel(sentimentScore, t) : null;

  const countdownText = marketOpen
    ? t("hero.closes_in", { time: formatCountdown(countdown.secondsLeft) })
    : t("hero.opens_in", { time: formatCountdown(countdown.secondsLeft) });

  const holdings = portfolio?.holdings ?? [];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3 mb-4 sm:mb-6">
      {/* Portfolio Value card with mini area chart background */}
      <div className="bg-oracle-panel border border-oracle-border rounded-xl overflow-hidden shadow-sm transition-all duration-300 hover:border-oracle-border-hover hover:shadow-md relative">
        <div className="h-[2px] bg-gradient-to-r from-[#12b5b0] to-[#0e9a96]" />
        <div className="p-3 sm:p-5 relative z-10">
          <p className="text-oracle-muted text-[10px] sm:text-xs font-semibold uppercase tracking-wide mb-1">
            {t("hero.portfolio_value")}
          </p>
          <p className="text-base sm:text-xl font-bold font-mono text-oracle-text">
            {portfolio ? formatPrice(portfolio.total_value) : "--"}
          </p>
          <p className="text-oracle-muted text-[10px] sm:text-xs mt-1">
            {portfolio
              ? t("hero.holdings", { count: String(portfolio.holdings.length) })
              : t("hero.loading")}
          </p>
        </div>
        {holdings.length > 0 && (
          <MiniPortfolioChart sparklines={sparklines} holdings={holdings} />
        )}
      </div>

      {/* Daily P&L card with contribution bar */}
      <div className="bg-oracle-panel border border-oracle-border rounded-xl overflow-hidden shadow-sm transition-all duration-300 hover:border-oracle-border-hover hover:shadow-md">
        <div className="h-[2px] bg-gradient-to-r from-[#12b5b0] to-[#0e9a96]" />
        <div className="p-3 sm:p-5">
          <p className="text-oracle-muted text-[10px] sm:text-xs font-semibold uppercase tracking-wide mb-1">
            {t("hero.daily_pnl")}
          </p>
          <p className={`text-base sm:text-xl font-bold font-mono ${portfolio ? (pnlPositive ? "text-oracle-green" : "text-oracle-red") : "text-oracle-text"}`}>
            {portfolio ? `${pnlPositive ? "+" : ""}${formatPrice(portfolio.daily_pnl)}` : "--"}
          </p>
          <p className={`text-[10px] sm:text-xs mt-1 ${portfolio ? (pnlPositive ? "text-oracle-green" : "text-oracle-red") : "text-oracle-muted"}`}>
            {portfolio ? `${pnlPositive ? "+" : ""}${portfolio.daily_pnl_percent.toFixed(2)}%` : t("hero.loading")}
          </p>
          {holdings.length > 0 && <PnlContributionBar holdings={holdings} />}
        </div>
      </div>

      {/* Market Status card */}
      <MarketStatusCard
        marketOpen={marketOpen}
        countdownText={countdownText}
        t={t}
      />

      {/* 4th card: Market Sentiment Gauge */}
      <div className="bg-oracle-panel border border-oracle-border rounded-xl overflow-hidden shadow-sm transition-all duration-300 hover:border-oracle-border-hover hover:shadow-md flex flex-col">
        <div className="h-[2px] bg-gradient-to-r from-[#12b5b0] to-[#0e9a96]" />
        <div className="p-3 sm:p-5 flex flex-col items-center justify-center flex-1">
          <p className="text-oracle-muted text-[10px] sm:text-xs font-semibold uppercase tracking-wide mb-1">
            {t("hero.sentiment")}
          </p>
          {sentimentScore !== null ? (
            <>
              <SentimentGauge score={sentimentScore} />
              <p className={`text-xs sm:text-sm font-bold mt-0.5 ${sentiment?.color || "text-oracle-text"}`}>
                {sentiment?.label}
              </p>
              <p className="text-oracle-muted text-[8px] sm:text-[10px] font-mono mt-0.5">
                VIX {vixValue?.toFixed(1)}
              </p>
            </>
          ) : (
            <div className="w-[80px] sm:w-[100px] h-[40px] sm:h-[50px] bg-oracle-bg rounded animate-pulse mt-1" />
          )}
        </div>
      </div>
    </div>
  );
}

export default function HeroMetrics() {
  const { activeView } = useView();
  const { t } = useLanguageStore();

  if (activeView === "overview") {
    return <OverviewHero />;
  }

  const titleKey = `view.${activeView}.title`;
  const descKey = `view.${activeView}.desc`;

  return (
    <div className="mb-6">
      <h1 className="text-oracle-text text-xl font-bold">{t(titleKey)}</h1>
      <p className="text-oracle-muted text-sm mt-0.5">{t(descKey)}</p>
      <div className="oracle-separator mt-3" />
    </div>
  );
}
