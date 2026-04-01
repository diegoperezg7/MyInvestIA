"use client";

import { useState } from "react";
import {
  Crosshair,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Brain,
  Globe,
  Newspaper,
  Users,
  Target,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertTriangle,
  Zap,
  Shield,
} from "lucide-react";
import { fetchAPI } from "@/lib/api";
import useLanguageStore from "@/stores/useLanguageStore";
import type { PredictionResponse, QuantScores } from "@/types";

const VERDICT_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; icon: React.ReactNode }
> = {
  strong_buy: {
    label: "prediction.strong_buy",
    color: "text-emerald-400",
    bg: "bg-emerald-500/15",
    border: "border-emerald-500/30",
    icon: <TrendingUp size={28} />,
  },
  buy: {
    label: "prediction.buy",
    color: "text-green-400",
    bg: "bg-green-500/15",
    border: "border-green-500/30",
    icon: <TrendingUp size={28} />,
  },
  neutral: {
    label: "prediction.neutral",
    color: "text-yellow-400",
    bg: "bg-yellow-500/15",
    border: "border-yellow-500/30",
    icon: <Target size={28} />,
  },
  sell: {
    label: "prediction.sell",
    color: "text-orange-400",
    bg: "bg-orange-500/15",
    border: "border-orange-500/30",
    icon: <TrendingDown size={28} />,
  },
  strong_sell: {
    label: "prediction.strong_sell",
    color: "text-red-400",
    bg: "bg-red-500/15",
    border: "border-red-500/30",
    icon: <TrendingDown size={28} />,
  },
};

function ConfidenceGauge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 70 ? "text-emerald-400" : pct >= 40 ? "text-yellow-400" : "text-red-400";
  const barColor =
    pct >= 70
      ? "bg-emerald-500"
      : pct >= 40
        ? "bg-yellow-500"
        : "bg-red-500";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-oracle-bg rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} rounded-full transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-sm font-mono font-bold ${color}`}>{pct}%</span>
    </div>
  );
}

function SectionCard({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-oracle-border bg-oracle-panel p-4 hover:border-oracle-border-hover transition-colors">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-oracle-accent">{icon}</span>
        <h3 className="text-sm font-semibold text-oracle-text">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function TagList({ items, color = "text-oracle-muted" }: { items: string[]; color?: string }) {
  if (!items.length) return <span className="text-xs text-oracle-muted">—</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item, i) => (
        <span
          key={i}
          className={`text-[11px] px-2 py-0.5 rounded bg-oracle-bg border border-oracle-border ${color}`}
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export default function PredictionView() {
  const t = useLanguageStore((s) => s.t);
  const [symbol, setSymbol] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState<PredictionResponse | null>(null);
  const [analysisExpanded, setAnalysisExpanded] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;

    setLoading(true);
    setError("");
    setData(null);

    try {
      const result = await fetchAPI<PredictionResponse>(
        `/api/v1/chat/predict/${sym}`,
        { skipCache: true }
      );
      setData(result);
    } catch {
      setError(t("prediction.error"));
    } finally {
      setLoading(false);
    }
  };

  const vc = data ? VERDICT_CONFIG[data.verdict] || VERDICT_CONFIG.neutral : null;

  return (
    <div className="space-y-4">
      {/* Header + Search */}
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <Crosshair size={22} className="text-oracle-accent" />
          <div>
            <h2 className="text-lg font-bold text-oracle-text">
              {t("view.prediction.title")}
            </h2>
            <p className="text-xs text-oracle-muted">{t("view.prediction.desc")}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder={t("quote.placeholder")}
            className="flex-1 px-3 py-2 bg-oracle-bg border border-oracle-border rounded-md text-sm text-oracle-text placeholder-oracle-muted focus:outline-none focus:border-oracle-accent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !symbol.trim()}
            className="px-5 py-2 rounded-md text-sm font-medium bg-oracle-accent text-white hover:opacity-90 disabled:opacity-40 transition-opacity flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                {t("prediction.loading")}
              </>
            ) : (
              <>
                <Crosshair size={16} />
                {t("prediction.generate")}
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-4 animate-pulse">
          <div className="h-32 bg-oracle-panel border border-oracle-border rounded-lg" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-40 bg-oracle-panel border border-oracle-border rounded-lg" />
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {data && vc && !loading && (
        <>
          {/* Hero Verdict Card */}
          <div
            className={`rounded-lg border ${vc.border} ${vc.bg} p-6`}
          >
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <div className={`${vc.color} shrink-0`}>{vc.icon}</div>
              <div className="flex-1 text-center sm:text-left">
                <div className="flex items-center justify-center sm:justify-start gap-3 mb-1">
                  <span className={`text-2xl font-black tracking-wide ${vc.color}`}>
                    {t(vc.label)}
                  </span>
                  <span className="text-sm font-mono text-oracle-muted">
                    {data.symbol}
                  </span>
                </div>
                <div className="max-w-xs">
                  <p className="text-[11px] text-oracle-muted mb-1">
                    {t("prediction.confidence")}
                  </p>
                  <ConfidenceGauge value={data.confidence} />
                </div>
              </div>
              <div className="text-xs text-oracle-muted text-right shrink-0">
                {data.generated_at &&
                  new Date(data.generated_at).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Quantitative Score Card */}
          {data.quant_scores && data.quant_scores.composite_score !== undefined && (
            <QuantScoreCard quant={data.quant_scores} />
          )}

          {/* 5-Section Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Technical */}
            <SectionCard
              title={t("prediction.technical")}
              icon={<BarChart3 size={16} />}
            >
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Signal</span>
                  <SignalBadge signal={data.technical_summary.signal} />
                </div>
                {data.technical_summary.support && data.technical_summary.support !== "N/A" && (
                  <div className="flex justify-between">
                    <span className="text-oracle-muted">Support</span>
                    <span className="text-oracle-text font-mono">
                      {data.technical_summary.support}
                    </span>
                  </div>
                )}
                {data.technical_summary.resistance && data.technical_summary.resistance !== "N/A" && (
                  <div className="flex justify-between">
                    <span className="text-oracle-muted">Resistance</span>
                    <span className="text-oracle-text font-mono">
                      {data.technical_summary.resistance}
                    </span>
                  </div>
                )}
                {data.technical_summary.key_indicators && (
                  <div className="pt-1 border-t border-oracle-border">
                    <TagList items={data.technical_summary.key_indicators} />
                  </div>
                )}
              </div>
            </SectionCard>

            {/* Sentiment */}
            <SectionCard
              title={t("prediction.sentiment")}
              icon={<Brain size={16} />}
            >
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Score</span>
                  <span
                    className={`font-mono font-bold ${
                      (data.sentiment_summary.unified_score ?? 0) > 0
                        ? "text-green-400"
                        : (data.sentiment_summary.unified_score ?? 0) < 0
                          ? "text-red-400"
                          : "text-yellow-400"
                    }`}
                  >
                    {(data.sentiment_summary.unified_score ?? 0) > 0 ? "+" : ""}
                    {(data.sentiment_summary.unified_score ?? 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Label</span>
                  <SignalBadge signal={data.sentiment_summary.label} />
                </div>
                {data.sentiment_summary.divergences && data.sentiment_summary.divergences.length > 0 && (
                  <div className="pt-1 border-t border-oracle-border">
                    <p className="text-oracle-muted mb-1 flex items-center gap-1">
                      <AlertTriangle size={11} className="text-yellow-400" />
                      Divergencias
                    </p>
                    {data.sentiment_summary.divergences.map((d, i) => (
                      <p key={i} className="text-[11px] text-yellow-400/80">{d}</p>
                    ))}
                  </div>
                )}
                {data.sentiment_summary.key_factors && (
                  <div className="pt-1 border-t border-oracle-border">
                    <TagList items={data.sentiment_summary.key_factors} />
                  </div>
                )}
              </div>
            </SectionCard>

            {/* Macro */}
            <SectionCard
              title={t("prediction.macro")}
              icon={<Globe size={16} />}
            >
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Environment</span>
                  <span className="text-oracle-text capitalize">
                    {data.macro_summary.environment || "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Risk</span>
                  <RiskBadge level={data.macro_summary.risk_level} />
                </div>
                <div className="flex justify-between">
                  <span className="text-oracle-muted">VIX Regime</span>
                  <span className="text-oracle-text capitalize">
                    {(data.macro_summary.vix_regime || "—").replace("_", " ")}
                  </span>
                </div>
                {data.macro_summary.impact_on_asset && (
                  <p className="pt-1 border-t border-oracle-border text-oracle-muted leading-relaxed">
                    {data.macro_summary.impact_on_asset}
                  </p>
                )}
              </div>
            </SectionCard>

            {/* News */}
            <SectionCard
              title={t("prediction.news")}
              icon={<Newspaper size={16} />}
            >
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Articles</span>
                  <span className="text-oracle-text font-mono">
                    {data.news_summary.headline_count ?? 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Tone</span>
                  <ToneBadge tone={data.news_summary.overall_tone} />
                </div>
                {data.news_summary.summary && (
                  <p className="text-oracle-muted leading-relaxed">
                    {data.news_summary.summary}
                  </p>
                )}
                {data.news_summary.top_headlines && data.news_summary.top_headlines.length > 0 && (
                  <div className="pt-1 border-t border-oracle-border space-y-1">
                    {data.news_summary.top_headlines.slice(0, 3).map((h, i) => (
                      <p key={i} className="text-[11px] text-oracle-muted truncate">
                        {h}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </SectionCard>

            {/* Social */}
            <SectionCard
              title={t("prediction.social")}
              icon={<Users size={16} />}
            >
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Mentions</span>
                  <span className="text-oracle-text font-mono">
                    {data.social_summary.total_mentions ?? 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Buzz</span>
                  <BuzzBadge level={data.social_summary.buzz_level} />
                </div>
                <div className="flex justify-between">
                  <span className="text-oracle-muted">Trend</span>
                  <span className="text-oracle-text capitalize">
                    {data.social_summary.trend || "—"}
                  </span>
                </div>
                {data.social_summary.summary && (
                  <p className="pt-1 border-t border-oracle-border text-oracle-muted leading-relaxed">
                    {data.social_summary.summary}
                  </p>
                )}
              </div>
            </SectionCard>
          </div>

          {/* Price Outlook */}
          <div className="bg-oracle-panel border border-oracle-border rounded-lg p-5">
            <div className="flex items-center gap-2 mb-4">
              <Target size={18} className="text-oracle-accent" />
              <h3 className="text-sm font-semibold text-oracle-text">
                {t("prediction.outlook")}
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div className="p-3 bg-oracle-bg rounded-lg border border-oracle-border">
                <p className="text-[11px] text-oracle-muted font-semibold uppercase tracking-wide mb-1.5">
                  {t("prediction.short_term")}
                </p>
                <p className="text-xs text-oracle-text leading-relaxed">
                  {data.price_outlook.short_term || "—"}
                </p>
              </div>
              <div className="p-3 bg-oracle-bg rounded-lg border border-oracle-border">
                <p className="text-[11px] text-oracle-muted font-semibold uppercase tracking-wide mb-1.5">
                  {t("prediction.medium_term")}
                </p>
                <p className="text-xs text-oracle-text leading-relaxed">
                  {data.price_outlook.medium_term || "—"}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="flex items-center gap-1 text-[11px] text-oracle-muted font-semibold uppercase tracking-wide mb-1.5">
                  <Zap size={11} className="text-green-400" />
                  {t("prediction.catalysts")}
                </p>
                <ul className="space-y-1">
                  {(data.price_outlook.catalysts || []).map((c, i) => (
                    <li
                      key={i}
                      className="text-xs text-oracle-text flex items-start gap-1.5"
                    >
                      <span className="text-green-400 mt-0.5 shrink-0">+</span>
                      {c}
                    </li>
                  ))}
                  {!(data.price_outlook.catalysts || []).length && (
                    <li className="text-xs text-oracle-muted">—</li>
                  )}
                </ul>
              </div>
              <div>
                <p className="flex items-center gap-1 text-[11px] text-oracle-muted font-semibold uppercase tracking-wide mb-1.5">
                  <Shield size={11} className="text-red-400" />
                  {t("prediction.risks")}
                </p>
                <ul className="space-y-1">
                  {(data.price_outlook.risks || []).map((r, i) => (
                    <li
                      key={i}
                      className="text-xs text-oracle-text flex items-start gap-1.5"
                    >
                      <span className="text-red-400 mt-0.5 shrink-0">!</span>
                      {r}
                    </li>
                  ))}
                  {!(data.price_outlook.risks || []).length && (
                    <li className="text-xs text-oracle-muted">—</li>
                  )}
                </ul>
              </div>
            </div>
          </div>

          {/* Full AI Analysis (expandable) */}
          <div className="bg-oracle-panel border border-oracle-border rounded-lg overflow-hidden">
            <button
              onClick={() => setAnalysisExpanded(!analysisExpanded)}
              className="w-full flex items-center justify-between p-5 hover:bg-oracle-panel-hover transition-colors"
            >
              <div className="flex items-center gap-2">
                <Brain size={18} className="text-oracle-accent" />
                <h3 className="text-sm font-semibold text-oracle-text">
                  {t("prediction.analysis")}
                </h3>
              </div>
              {analysisExpanded ? (
                <ChevronUp size={16} className="text-oracle-muted" />
              ) : (
                <ChevronDown size={16} className="text-oracle-muted" />
              )}
            </button>
            {analysisExpanded && (
              <div className="px-5 pb-5 border-t border-oracle-border">
                <div className="pt-4 text-sm text-oracle-text leading-relaxed whitespace-pre-wrap">
                  {data.ai_analysis}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Empty state */}
      {!data && !loading && !error && (
        <div className="text-center py-16 text-oracle-muted">
          <Crosshair size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">{t("prediction.enter_symbol")}</p>
        </div>
      )}
    </div>
  );
}

/* Quantitative Score Card */

const FACTOR_LABELS: Record<string, string> = {
  trend: "Tendencia",
  mean_reversion: "Reversión",
  momentum: "Momentum",
  volume: "Volumen",
  support_resistance: "Soporte/Resist.",
  candlestick: "Velas",
  macro: "Macro",
  sentiment: "Sentimiento",
};

function FactorBar({ name, value, weight }: { name: string; value: number; weight: number }) {
  const color = value > 0.15 ? "bg-emerald-500" : value < -0.15 ? "bg-red-500" : "bg-yellow-500";
  const textColor = value > 0.15 ? "text-emerald-400" : value < -0.15 ? "text-red-400" : "text-yellow-400";

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-28 text-oracle-muted truncate" title={name}>
        {FACTOR_LABELS[name] || name}
      </span>
      <div className="flex-1 h-2 bg-oracle-bg rounded-full overflow-hidden relative">
        <div className="absolute left-1/2 top-0 w-px h-full bg-oracle-border z-10" />
        <div
          className={`absolute top-0 h-full ${color} rounded-full transition-all duration-500`}
          style={
            value >= 0
              ? { left: "50%", width: `${(value / 1) * 50}%` }
              : { right: "50%", width: `${(Math.abs(value) / 1) * 50}%` }
          }
        />
      </div>
      <span className={`w-12 text-right font-mono font-bold ${textColor}`}>
        {value > 0 ? "+" : ""}{value.toFixed(2)}
      </span>
      <span className="w-10 text-right text-oracle-muted font-mono text-[10px]">
        {Math.round(weight * 100)}%
      </span>
    </div>
  );
}

function QuantScoreCard({ quant }: { quant: QuantScores }) {
  const composite = quant.composite_score;
  const compositeColor =
    composite > 0.25
      ? "text-emerald-400"
      : composite < -0.25
        ? "text-red-400"
        : "text-yellow-400";
  const compositeBarColor =
    composite > 0.25
      ? "bg-emerald-500"
      : composite < -0.25
        ? "bg-red-500"
        : "bg-yellow-500";

  const sr = quant.support_resistance || {};
  const risk = quant.risk_metrics || { sharpe_ratio: 0, max_drawdown: 0, historical_volatility: 0 };
  const patterns = quant.candlestick_patterns || [];

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 size={18} className="text-oracle-accent" />
          <h3 className="text-sm font-semibold text-oracle-text">Motor Cuantitativo</h3>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-[11px] font-medium px-2 py-0.5 rounded ${
              quant.regime === "trending"
                ? "text-blue-400 bg-blue-500/10"
                : quant.regime === "range_bound"
                  ? "text-purple-400 bg-purple-500/10"
                  : "text-oracle-muted bg-oracle-bg"
            }`}
          >
            {quant.regime === "trending"
              ? "Tendencial"
              : quant.regime === "range_bound"
                ? "Rango"
                : "—"}
          </span>
          <span className="text-[10px] text-oracle-muted font-mono">
            ADX {quant.adx?.toFixed(1)}
          </span>
          {quant.factor_agreement != null && (
            <span
              className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                quant.factor_agreement >= 1.15
                  ? "text-emerald-400 bg-emerald-500/10"
                  : quant.factor_agreement <= 0.85
                    ? "text-red-400 bg-red-500/10"
                    : "text-yellow-400 bg-yellow-500/10"
              }`}
            >
              {quant.factor_agreement >= 1.15
                ? "Alta Conviccion"
                : quant.factor_agreement <= 0.85
                  ? "Factores Divididos"
                  : "Conviccion Moderada"}
            </span>
          )}
        </div>
      </div>

      {/* Composite Score */}
      <div className="mb-4 p-3 bg-oracle-bg rounded-lg border border-oracle-border">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-oracle-muted font-semibold uppercase tracking-wide">
            Score Compuesto
          </span>
          <span className={`text-lg font-black font-mono ${compositeColor}`}>
            {composite > 0 ? "+" : ""}{composite.toFixed(4)}
          </span>
        </div>
        <div className="h-3 bg-oracle-panel rounded-full overflow-hidden relative">
          <div className="absolute left-1/2 top-0 w-px h-full bg-oracle-border z-10" />
          <div
            className={`absolute top-0 h-full ${compositeBarColor} rounded-full transition-all duration-700`}
            style={
              composite >= 0
                ? { left: "50%", width: `${(composite / 1) * 50}%` }
                : { right: "50%", width: `${(Math.abs(composite) / 1) * 50}%` }
            }
          />
        </div>
        <div className="flex justify-between mt-1 text-[10px] text-oracle-muted font-mono">
          <span>-1.0</span>
          <span>0</span>
          <span>+1.0</span>
        </div>
      </div>

      {/* Factor Bars */}
      <div className="space-y-1.5 mb-4">
        {Object.entries(quant.factors || {}).map(([name, value]) => (
          <FactorBar
            key={name}
            name={name}
            value={value}
            weight={quant.weights?.[name] ?? 0}
          />
        ))}
      </div>

      {/* Bottom row: S/R + Risk + Patterns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-3 border-t border-oracle-border">
        {/* Support/Resistance */}
        <div className="space-y-1">
          <p className="text-[10px] text-oracle-muted font-semibold uppercase tracking-wide">
            Soporte / Resistencia
          </p>
          {sr.nearest_support != null && (
            <div className="flex justify-between text-xs">
              <span className="text-oracle-muted">Soporte</span>
              <span className="text-green-400 font-mono">${sr.nearest_support}</span>
            </div>
          )}
          {sr.nearest_resistance != null && (
            <div className="flex justify-between text-xs">
              <span className="text-oracle-muted">Resistencia</span>
              <span className="text-red-400 font-mono">${sr.nearest_resistance}</span>
            </div>
          )}
          {sr.pivot != null && (
            <div className="flex justify-between text-xs">
              <span className="text-oracle-muted">Pivot</span>
              <span className="text-oracle-text font-mono">${sr.pivot}</span>
            </div>
          )}
        </div>

        {/* Risk Metrics */}
        <div className="space-y-1">
          <p className="text-[10px] text-oracle-muted font-semibold uppercase tracking-wide">
            Riesgo
          </p>
          <div className="flex justify-between text-xs">
            <span className="text-oracle-muted">Sharpe (63d)</span>
            <span
              className={`font-mono font-bold ${
                risk.sharpe_ratio > 0.5
                  ? "text-emerald-400"
                  : risk.sharpe_ratio < 0
                    ? "text-red-400"
                    : "text-yellow-400"
              }`}
            >
              {risk.sharpe_ratio.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-oracle-muted">Max DD (63d)</span>
            <span className="text-red-400 font-mono">{risk.max_drawdown.toFixed(1)}%</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-oracle-muted">Vol (20d)</span>
            <span className="text-oracle-text font-mono">{risk.historical_volatility.toFixed(1)}%</span>
          </div>
        </div>

        {/* Candlestick Patterns */}
        <div className="space-y-1">
          <p className="text-[10px] text-oracle-muted font-semibold uppercase tracking-wide">
            Patrones
          </p>
          {patterns.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {patterns.map((p, i) => (
                <span
                  key={i}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-oracle-bg border border-oracle-border text-oracle-text"
                >
                  {p}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-xs text-oracle-muted">Sin patrones detectados</span>
          )}
        </div>
      </div>
    </div>
  );
}

/* Small badge components */

function SignalBadge({ signal }: { signal?: string }) {
  if (!signal) return <span className="text-oracle-muted">—</span>;
  const color =
    signal === "bullish"
      ? "text-green-400 bg-green-500/10"
      : signal === "bearish"
        ? "text-red-400 bg-red-500/10"
        : "text-yellow-400 bg-yellow-500/10";
  return (
    <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded ${color} capitalize`}>
      {signal}
    </span>
  );
}

function RiskBadge({ level }: { level?: string }) {
  if (!level) return <span className="text-oracle-muted">—</span>;
  const color =
    level === "low"
      ? "text-green-400 bg-green-500/10"
      : level === "moderate"
        ? "text-yellow-400 bg-yellow-500/10"
        : level === "elevated"
          ? "text-orange-400 bg-orange-500/10"
          : "text-red-400 bg-red-500/10";
  return (
    <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded ${color} capitalize`}>
      {level}
    </span>
  );
}

function ToneBadge({ tone }: { tone?: string }) {
  if (!tone) return <span className="text-oracle-muted">—</span>;
  const color =
    tone === "positive"
      ? "text-green-400 bg-green-500/10"
      : tone === "negative"
        ? "text-red-400 bg-red-500/10"
        : tone === "mixed"
          ? "text-yellow-400 bg-yellow-500/10"
          : "text-oracle-muted bg-oracle-bg";
  return (
    <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded ${color} capitalize`}>
      {tone}
    </span>
  );
}

function BuzzBadge({ level }: { level?: string }) {
  if (!level || level === "none")
    return <span className="text-oracle-muted text-[11px]">none</span>;
  const color =
    level === "viral"
      ? "text-purple-400 bg-purple-500/10"
      : level === "high"
        ? "text-orange-400 bg-orange-500/10"
        : level === "moderate"
          ? "text-yellow-400 bg-yellow-500/10"
          : "text-oracle-muted bg-oracle-bg";
  return (
    <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded ${color} capitalize`}>
      {level}
    </span>
  );
}
