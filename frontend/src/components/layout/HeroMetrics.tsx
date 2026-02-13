"use client";

import { useEffect, useState } from "react";
import { useView, type View } from "@/contexts/ViewContext";
import { fetchAPI } from "@/lib/api";
import useLanguageStore from "@/stores/useLanguageStore";
import useCurrencyStore from "@/stores/useCurrencyStore";
import type { Portfolio, MacroIntelligenceResponse } from "@/types";

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

  const cards = [
    {
      label: t("hero.portfolio_value"),
      value: portfolio ? formatPrice(portfolio.total_value) : "--",
      sub: portfolio
        ? t("hero.holdings", { count: String(portfolio.holdings.length) })
        : t("hero.loading"),
    },
    {
      label: t("hero.daily_pnl"),
      value: portfolio ? `${pnlPositive ? "+" : ""}${formatPrice(portfolio.daily_pnl)}` : "--",
      sub: portfolio ? `${pnlPositive ? "+" : ""}${portfolio.daily_pnl_percent.toFixed(2)}%` : t("hero.loading"),
      color: portfolio ? (pnlPositive ? "text-oracle-green" : "text-oracle-red") : undefined,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-oracle-panel border border-oracle-border rounded-xl overflow-hidden shadow-sm transition-all duration-300 hover:border-oracle-border-hover hover:shadow-md"
        >
          <div className="h-[2px] bg-gradient-to-r from-[#12b5b0] to-[#0e9a96]" />
          <div className="p-5">
            <p className="text-oracle-muted text-xs font-semibold uppercase tracking-wide mb-1">
              {card.label}
            </p>
            <p className={`text-xl font-bold font-mono ${card.color || "text-oracle-text"}`}>
              {card.value}
            </p>
            <p className="text-oracle-muted text-xs mt-1">{card.sub}</p>
          </div>
        </div>
      ))}

      {/* Market Status card with countdown */}
      <div className="bg-oracle-panel border border-oracle-border rounded-xl overflow-hidden shadow-sm transition-all duration-300 hover:border-oracle-border-hover hover:shadow-md">
        <div className="h-[2px] bg-gradient-to-r from-[#12b5b0] to-[#0e9a96]" />
        <div className="p-5">
          <p className="text-oracle-muted text-xs font-semibold uppercase tracking-wide mb-1">
            {t("hero.market_status")}
          </p>
          <p className={`text-xl font-bold font-mono ${marketOpen ? "text-oracle-green" : "text-oracle-muted"}`}>
            {marketOpen ? t("hero.open") : t("hero.closed")}
          </p>
          <p className="text-oracle-muted text-xs mt-1">{t("hero.us_markets")}</p>
          <p className={`font-mono text-xs mt-1.5 ${marketOpen ? "text-oracle-yellow" : "text-oracle-accent"}`}>
            {countdownText}
          </p>
        </div>
      </div>

      {/* 4th card: Market Sentiment Gauge */}
      <div className="bg-oracle-panel border border-oracle-border rounded-xl overflow-hidden shadow-sm transition-all duration-300 hover:border-oracle-border-hover hover:shadow-md flex flex-col">
        <div className="h-[2px] bg-gradient-to-r from-[#12b5b0] to-[#0e9a96]" />
        <div className="p-5 flex flex-col items-center justify-center flex-1">
          <p className="text-oracle-muted text-xs font-semibold uppercase tracking-wide mb-1">
            {t("hero.sentiment")}
          </p>
          {sentimentScore !== null ? (
            <>
              <SentimentGauge score={sentimentScore} />
              <p className={`text-sm font-bold mt-0.5 ${sentiment?.color || "text-oracle-text"}`}>
                {sentiment?.label}
              </p>
              <p className="text-oracle-muted text-[10px] font-mono mt-0.5">
                VIX {vixValue?.toFixed(1)}
              </p>
            </>
          ) : (
            <div className="w-[100px] h-[50px] bg-oracle-bg rounded animate-pulse mt-1" />
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
