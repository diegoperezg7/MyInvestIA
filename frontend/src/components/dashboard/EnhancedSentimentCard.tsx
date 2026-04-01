"use client";

import { useReducer } from "react";
import { fetchAPI } from "@/lib/api";
import type {
  SentimentAnalysis,
  SocialSentimentData,
  EnhancedSentimentResponse,
} from "@/types";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";

const LABEL_COLORS: Record<string, string> = {
  bullish: "text-oracle-green",
  bearish: "text-oracle-red",
  neutral: "text-oracle-muted",
};

const LABEL_BG: Record<string, string> = {
  bullish: "bg-oracle-green/20 border-oracle-green/30",
  bearish: "bg-oracle-red/20 border-oracle-red/30",
  neutral: "bg-oracle-muted/20 border-oracle-muted/30",
};

const BUZZ_COLORS: Record<string, string> = {
  viral: "text-oracle-accent bg-oracle-accent/20 border-oracle-accent/30",
  high: "text-oracle-green bg-oracle-green/20 border-oracle-green/30",
  moderate: "text-oracle-text bg-oracle-muted/20 border-oracle-muted/30",
  low: "text-oracle-muted bg-oracle-bg border-oracle-border",
  none: "text-oracle-muted bg-oracle-bg border-oracle-border",
};

function ScoreBar({ score, label }: { score: number; label?: string }) {
  const percent = ((score + 1) / 2) * 100;
  const barColor =
    score > 0.2
      ? "bg-oracle-green"
      : score < -0.2
        ? "bg-oracle-red"
        : "bg-oracle-accent";

  return (
    <div className="w-full">
      {label && <p className="text-xs text-oracle-muted mb-1">{label}</p>}
      <div className="flex justify-between text-xs text-oracle-muted mb-1">
        <span>Bearish</span>
        <span>Neutral</span>
        <span>Bullish</span>
      </div>
      <div className="relative h-2 bg-oracle-bg rounded-full overflow-hidden">
        <div className="absolute left-1/2 top-0 w-px h-full bg-oracle-border z-10" />
        <div
          className={`absolute top-0 h-full w-3 rounded-full ${barColor}`}
          style={{ left: `calc(${percent}% - 6px)` }}
        />
      </div>
      <div className="text-center mt-1">
        <span className="text-sm font-mono text-oracle-text">
          {score > 0 ? "+" : ""}
          {score.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

function SourceContributionBar({
  sources,
}: {
  sources: EnhancedSentimentResponse["sources"];
}) {
  const SOURCE_COLORS: Record<string, string> = {
    "AI Sentiment": "bg-oracle-accent",
    "Social Pulse": "bg-cyan-400",
    "News Coverage": "bg-oracle-yellow",
  };

  return (
    <div className="space-y-2">
      <p className="text-xs text-oracle-muted uppercase tracking-wide">
        Fuentes de Sentimiento
      </p>
      {/* Stacked contribution bar */}
      <div className="h-2.5 bg-oracle-bg rounded-full overflow-hidden flex">
        {sources.map((src, i) => {
          const widthPct = src.weight * 100;
          const color = SOURCE_COLORS[src.source_name] || "bg-oracle-muted";
          return (
            <div
              key={src.source_name}
              className={`h-full ${color} ${i === 0 ? "rounded-l-full" : ""} ${
                i === sources.length - 1 ? "rounded-r-full" : ""
              }`}
              style={{ width: `${widthPct}%` }}
              title={`${src.source_name}: ${(src.weight * 100).toFixed(0)}%`}
            />
          );
        })}
      </div>
      {/* Source breakdown */}
      <div className="space-y-1.5">
        {sources.map((src) => {
          const color = SOURCE_COLORS[src.source_name] || "bg-oracle-muted";
          const scoreColor =
            src.score > 0.1
              ? "text-oracle-green"
              : src.score < -0.1
                ? "text-oracle-red"
                : "text-oracle-muted";
          return (
            <div key={src.source_name} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${color}`} />
                <span className="text-oracle-text">{src.source_name}</span>
                <span className="text-oracle-muted">
                  ({(src.weight * 100).toFixed(0)}%)
                </span>
              </div>
              <span className={`font-mono ${scoreColor}`}>
                {src.score > 0 ? "+" : ""}
                {src.score.toFixed(3)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SocialBuzzSection({ data }: { data: SocialSentimentData }) {
  return (
    <div className="space-y-3 border-t border-oracle-border pt-3 mt-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-oracle-muted uppercase tracking-wide">
          Social Buzz (24h)
        </p>
        <span
          className={`px-2 py-0.5 text-xs font-medium uppercase rounded border ${BUZZ_COLORS[data.buzz_level]}`}
        >
          {data.buzz_level}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-oracle-bg rounded p-2 text-center">
          <p className="text-lg font-bold text-oracle-text">
            {data.total_mentions}
          </p>
          <p className="text-xs text-oracle-muted">Total</p>
        </div>
        <div className="bg-oracle-bg rounded p-2 text-center">
          <p className="text-lg font-bold text-oracle-text">
            {data.reddit.mentions}
          </p>
          <p className="text-xs text-oracle-muted">Reddit</p>
        </div>
        <div className="bg-oracle-bg rounded p-2 text-center">
          <p className="text-lg font-bold text-oracle-text">
            {data.twitter.mentions}
          </p>
          <p className="text-xs text-oracle-muted">Twitter</p>
        </div>
      </div>
      <ScoreBar score={data.combined_score} label="Social Sentiment Score" />
    </div>
  );
}

interface SentimentState {
  symbol: string;
  data: SentimentAnalysis | null;
  socialData: SocialSentimentData | null;
  enhancedData: EnhancedSentimentResponse | null;
  loading: boolean;
  error: string | null;
}

type SentimentAction =
  | { type: "set_symbol"; symbol: string }
  | { type: "analyze_start" }
  | {
      type: "analyze_complete";
      data: SentimentAnalysis | null;
      socialData: SocialSentimentData | null;
      enhancedData: EnhancedSentimentResponse | null;
      error: string | null;
    }
  | { type: "analyze_error"; error: string };

const INITIAL_STATE: SentimentState = {
  symbol: "",
  data: null,
  socialData: null,
  enhancedData: null,
  loading: false,
  error: null,
};

function sentimentReducer(
  state: SentimentState,
  action: SentimentAction
): SentimentState {
  switch (action.type) {
    case "set_symbol":
      return { ...state, symbol: action.symbol };
    case "analyze_start":
      return {
        ...state,
        data: null,
        socialData: null,
        enhancedData: null,
        loading: true,
        error: null,
      };
    case "analyze_complete":
      return {
        ...state,
        data: action.data,
        socialData: action.socialData,
        enhancedData: action.enhancedData,
        loading: false,
        error: action.error,
      };
    case "analyze_error":
      return {
        ...state,
        loading: false,
        error: action.error,
      };
    default:
      return state;
  }
}

export default function EnhancedSentimentCard() {
  const [state, dispatch] = useReducer(sentimentReducer, INITIAL_STATE);
  const { symbol, data, socialData, enhancedData, loading, error } = state;

  async function handleAnalyze(nextSymbol?: string) {
    const s = (nextSymbol ?? symbol).trim().toUpperCase();
    if (!s) return;

    dispatch({ type: "set_symbol", symbol: s });
    dispatch({ type: "analyze_start" });

    try {
      const [aiResult, socialResult, enhancedResult] =
        await Promise.allSettled([
          fetchAPI<SentimentAnalysis>(`/api/v1/market/sentiment/${s}`),
          fetchAPI<SocialSentimentData>(`/api/v1/market/social-sentiment/${s}`),
          fetchAPI<EnhancedSentimentResponse>(
            `/api/v1/market/enhanced-sentiment/${s}`
          ),
        ]);

      const analyzeError =
        aiResult.status === "rejected" &&
        socialResult.status === "rejected" &&
        enhancedResult.status === "rejected"
          ? "Error al analizar sentimiento"
          : null;

      dispatch({
        type: "analyze_complete",
        data: aiResult.status === "fulfilled" ? aiResult.value : null,
        socialData: socialResult.status === "fulfilled" ? socialResult.value : null,
        enhancedData: enhancedResult.status === "fulfilled" ? enhancedResult.value : null,
        error: analyzeError,
      });
    } catch (e) {
      dispatch({
        type: "analyze_error",
        error: e instanceof Error ? e.message : "Error al analizar sentimiento",
      });
    }
  }

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide mb-3">
        Sentimiento Multi-Fuente
      </h3>

      {/* Search */}
      <div className="flex gap-2 mb-4">
        <SymbolAutocomplete
          value={symbol}
          onChange={(nextSymbol) =>
            dispatch({ type: "set_symbol", symbol: nextSymbol })
          }
          onSubmit={(s) => {
            void handleAnalyze(s);
          }}
          placeholder="Ingresa símbolo (ej: AAPL)"
          className="flex-1"
        />
        <button
          onClick={() => void handleAnalyze()}
          disabled={loading || !symbol.trim()}
          className="px-3 py-1.5 text-sm bg-oracle-accent/20 text-oracle-accent border border-oracle-accent/30 rounded hover:bg-oracle-accent/30 disabled:opacity-50"
        >
          {loading ? "Analizando..." : "Analizar"}
        </button>
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {/* Enhanced unified score (top) */}
      {enhancedData && (
        <div className="space-y-4 mb-4">
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold text-oracle-text">
              {enhancedData.symbol}
            </span>
            <div className="flex items-center gap-2">
              {socialData && socialData.buzz_level !== "none" && (
                <span
                  className={`px-2 py-0.5 text-xs font-medium uppercase rounded border ${BUZZ_COLORS[socialData.buzz_level]}`}
                >
                  {socialData.buzz_level} buzz
                </span>
              )}
              <span
                className={`px-2 py-0.5 text-xs font-medium uppercase rounded border ${LABEL_BG[enhancedData.unified_label]}`}
              >
                <span className={LABEL_COLORS[enhancedData.unified_label]}>
                  {enhancedData.unified_label}
                </span>
              </span>
            </div>
          </div>

          <ScoreBar
            score={enhancedData.unified_score}
            label="Score Unificado"
          />

          {enhancedData.total_data_points > 0 && (
            <p className="text-xs text-oracle-muted">
              Basado en {enhancedData.total_data_points} data points
            </p>
          )}

          <div className="grid grid-cols-3 gap-2">
            <div className="bg-oracle-bg rounded p-2">
              <p className="text-[10px] uppercase text-oracle-muted mb-1">Coverage</p>
              <p className="text-sm font-mono text-oracle-text">
                {(enhancedData.coverage_confidence * 100).toFixed(0)}%
              </p>
            </div>
            <div className="bg-oracle-bg rounded p-2">
              <p className="text-[10px] uppercase text-oracle-muted mb-1">News Mom.</p>
              <p className={`text-sm font-mono ${enhancedData.news_momentum >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                {enhancedData.news_momentum > 0 ? "+" : ""}
                {enhancedData.news_momentum.toFixed(2)}
              </p>
            </div>
            <div className="bg-oracle-bg rounded p-2">
              <p className="text-[10px] uppercase text-oracle-muted mb-1">Social Mom.</p>
              <p className={`text-sm font-mono ${enhancedData.social_momentum >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                {enhancedData.social_momentum > 0 ? "+" : ""}
                {enhancedData.social_momentum.toFixed(2)}
              </p>
            </div>
          </div>

          {/* Source contribution */}
          <SourceContributionBar sources={enhancedData.sources} />

          {enhancedData.top_narratives.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-oracle-muted uppercase tracking-wide">Narrativas</p>
              {enhancedData.top_narratives.slice(0, 3).map((narrative) => (
                <div key={`${narrative.label}-${narrative.symbols.join("-")}`} className="bg-oracle-bg rounded p-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-oracle-text">{narrative.label}</span>
                    <span className={`text-xs font-mono ${narrative.avg_sentiment >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                      {narrative.avg_sentiment > 0 ? "+" : ""}
                      {narrative.avg_sentiment.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-oracle-muted">
                    {narrative.mentions} menciones
                    {narrative.symbols.length > 0 ? ` · ${narrative.symbols.join(", ")}` : ""}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* AI Sentiment details */}
      {data && !enhancedData && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold text-oracle-text">
              {data.symbol}
            </span>
            <span
              className={`px-2 py-0.5 text-xs font-medium uppercase rounded border ${LABEL_BG[data.label]}`}
            >
              <span className={LABEL_COLORS[data.label]}>{data.label}</span>
            </span>
          </div>
          <ScoreBar score={data.score} label="AI Sentiment Score" />
        </div>
      )}

      {/* Narrative */}
      {data && (
        <div className="mt-3 space-y-3">
          <p className="text-sm text-oracle-text leading-relaxed">
            {data.narrative}
          </p>
          {data.key_factors.length > 0 && (
            <div>
              <p className="text-xs text-oracle-muted uppercase mb-1">
                Factores Clave
              </p>
              <ul className="space-y-1">
                {data.key_factors.map((factor) => (
                  <li
                    key={factor}
                    className="text-xs text-oracle-text flex gap-2"
                  >
                    <span className="text-oracle-accent shrink-0">*</span>
                    {factor}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Social section */}
      {socialData && <SocialBuzzSection data={socialData} />}

      {!data && !socialData && !enhancedData && !loading && !error && (
        <p className="text-oracle-muted text-sm">
          Ingresa un símbolo para obtener análisis de sentimiento multi-fuente
          (IA + Social + Noticias).
        </p>
      )}
    </div>
  );
}
