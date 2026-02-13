"use client";

import { useState } from "react";
import { useRecommendations } from "@/hooks/useRecommendations";
import type { Recommendation } from "@/types";
import {
  TrendingUp,
  AlertTriangle,
  Scale,
  Activity,
  Globe,
  Users,
  Calendar,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const CATEGORY_CONFIG: Record<
  Recommendation["category"],
  { color: string; icon: React.ElementType; label: string }
> = {
  opportunity: { color: "text-oracle-green", icon: TrendingUp, label: "Oportunidad" },
  risk_alert: { color: "text-oracle-red", icon: AlertTriangle, label: "Alerta de Riesgo" },
  rebalance: { color: "text-oracle-info", icon: Scale, label: "Rebalanceo" },
  trend: { color: "text-oracle-accent", icon: Activity, label: "Tendencia" },
  macro_shift: { color: "text-oracle-yellow", icon: Globe, label: "Cambio Macro" },
  social_signal: { color: "text-oracle-accent", icon: Users, label: "Señal Social" },
  earnings_watch: { color: "text-oracle-yellow", icon: Calendar, label: "Vigilar Earnings" },
  sector_rotation: { color: "text-oracle-info", icon: RefreshCw, label: "Rotación Sectorial" },
};

const URGENCY_DOT: Record<string, string> = {
  high: "bg-oracle-red",
  medium: "bg-oracle-yellow",
  low: "bg-oracle-muted",
};

function MoodBar({ score }: { score: number }) {
  const percent = ((score + 1) / 2) * 100;
  const barColor =
    score > 0.2
      ? "bg-oracle-green"
      : score < -0.2
        ? "bg-oracle-red"
        : "bg-oracle-yellow";

  return (
    <div className="w-full max-w-xs">
      <div className="flex justify-between text-[10px] text-oracle-muted mb-0.5">
        <span>Bearish</span>
        <span>Neutral</span>
        <span>Bullish</span>
      </div>
      <div className="relative h-1.5 bg-oracle-bg rounded-full overflow-hidden">
        <div className="absolute left-1/2 top-0 w-px h-full bg-oracle-border z-10" />
        <div
          className={`absolute top-0 h-full w-3 rounded-full ${barColor} transition-all duration-500`}
          style={{ left: `calc(${percent}% - 6px)` }}
        />
      </div>
      <p className="text-center mt-0.5 text-xs font-mono text-oracle-muted">
        {score > 0 ? "+" : ""}{score.toFixed(2)}
      </p>
    </div>
  );
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const [expanded, setExpanded] = useState(false);
  const config = CATEGORY_CONFIG[rec.category];
  const Icon = config.icon;

  return (
    <div className="rounded-lg border border-oracle-border bg-oracle-panel p-4 hover:border-oracle-border-hover transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2">
          <Icon className={`w-3.5 h-3.5 ${config.color} shrink-0`} />
          <span className={`text-[11px] font-medium ${config.color}`}>
            {config.label}
          </span>
        </div>
        <span
          className={`w-1.5 h-1.5 rounded-full shrink-0 ${URGENCY_DOT[rec.urgency]}`}
          title={`Urgencia: ${rec.urgency}`}
        />
      </div>

      {/* Title */}
      <h4 className="text-sm font-medium text-oracle-text mb-1">
        {rec.title}
      </h4>

      {/* Reasoning */}
      <div className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <p className={`text-xs text-oracle-muted leading-relaxed ${expanded ? "" : "line-clamp-2"}`}>
          {rec.reasoning}
        </p>
        {rec.reasoning.length > 100 && (
          <button className="text-[11px] text-oracle-muted hover:text-oracle-text mt-0.5 flex items-center gap-0.5">
            {expanded ? <>Menos <ChevronUp className="w-3 h-3" /></> : <>Más <ChevronDown className="w-3 h-3" /></>}
          </button>
        )}
      </div>

      {/* Confidence */}
      <div className="mt-2.5">
        <div className="flex justify-between text-[10px] text-oracle-muted mb-0.5">
          <span>Confianza</span>
          <span>{Math.round(rec.confidence * 100)}%</span>
        </div>
        <div className="h-1 bg-oracle-bg rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-oracle-accent/60 transition-all"
            style={{ width: `${rec.confidence * 100}%` }}
          />
        </div>
      </div>

      {/* Tickers + Action */}
      <div className="flex items-center justify-between mt-2.5 gap-2">
        {rec.tickers.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {rec.tickers.map((t) => (
              <span
                key={t}
                className="text-[11px] font-mono px-1.5 py-0.5 bg-oracle-bg border border-oracle-border rounded text-oracle-text"
              >
                {t}
              </span>
            ))}
          </div>
        )}
        {rec.action && (
          <p className="text-[11px] text-oracle-muted shrink-0 text-right">
            {rec.action}
          </p>
        )}
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-lg border border-oracle-border bg-oracle-panel p-4 animate-pulse">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-3.5 h-3.5 rounded bg-oracle-bg" />
        <div className="w-16 h-3 rounded bg-oracle-bg" />
      </div>
      <div className="w-3/4 h-3.5 rounded bg-oracle-bg mb-2" />
      <div className="w-full h-3 rounded bg-oracle-bg mb-1" />
      <div className="w-2/3 h-3 rounded bg-oracle-bg" />
      <div className="w-full h-1 rounded bg-oracle-bg mt-3" />
    </div>
  );
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "ahora";
  if (mins < 60) return `hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `hace ${hrs}h`;
  return `hace ${Math.floor(hrs / 24)}d`;
}

export default function RecommendationsPanel() {
  const { data, loading, error, refresh } = useRecommendations();

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          Recomendaciones
        </h3>
        <div className="flex items-center gap-3">
          {data?.generated_at && (
            <span className="text-[11px] text-oracle-muted">
              {timeAgo(data.generated_at)}
            </span>
          )}
          <button
            onClick={refresh}
            disabled={loading}
            className="p-1 rounded text-oracle-muted hover:text-oracle-text hover:bg-oracle-bg transition-colors disabled:opacity-50"
            title="Actualizar"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {/* Loading */}
      {loading && !data && (
        <>
          <div className="w-full h-12 rounded bg-oracle-bg animate-pulse mb-4" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </>
      )}

      {/* Content */}
      {data && (
        <>
          {/* Market Mood */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4 p-3 bg-oracle-bg rounded-lg border border-oracle-border">
            <p className="flex-1 text-sm text-oracle-text leading-relaxed">
              {data.market_mood}
            </p>
            <MoodBar score={data.mood_score} />
          </div>

          {/* Grid */}
          {data.recommendations.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {data.recommendations.map((rec, i) => (
                <RecommendationCard key={i} rec={rec} />
              ))}
            </div>
          ) : (
            <p className="text-oracle-muted text-sm text-center py-4">
              No hay recomendaciones disponibles. Agrega activos a tu portafolio o watchlist.
            </p>
          )}
        </>
      )}
    </div>
  );
}
