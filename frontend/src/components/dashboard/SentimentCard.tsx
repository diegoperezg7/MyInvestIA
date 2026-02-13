"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { SentimentAnalysis, SocialSentimentData } from "@/types";
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
  // score is -1.0 to 1.0, map to 0-100%
  const percent = ((score + 1) / 2) * 100;
  const barColor =
    score > 0.2
      ? "bg-oracle-green"
      : score < -0.2
        ? "bg-oracle-red"
        : "bg-oracle-accent";

  return (
    <div className="w-full">
      {label && (
        <p className="text-xs text-oracle-muted mb-1">{label}</p>
      )}
      <div className="flex justify-between text-xs text-oracle-muted mb-1">
        <span>Bearish</span>
        <span>Neutral</span>
        <span>Bullish</span>
      </div>
      <div className="relative h-2 bg-oracle-bg rounded-full overflow-hidden">
        {/* Center marker */}
        <div className="absolute left-1/2 top-0 w-px h-full bg-oracle-border z-10" />
        {/* Score indicator */}
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

      {/* Mention counts */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-oracle-bg rounded p-2 text-center">
          <p className="text-lg font-bold text-oracle-text">{data.total_mentions}</p>
          <p className="text-xs text-oracle-muted">Total</p>
        </div>
        <div className="bg-oracle-bg rounded p-2 text-center">
          <p className="text-lg font-bold text-oracle-text">{data.reddit.mentions}</p>
          <p className="text-xs text-oracle-muted">Reddit</p>
        </div>
        <div className="bg-oracle-bg rounded p-2 text-center">
          <p className="text-lg font-bold text-oracle-text">{data.twitter.mentions}</p>
          <p className="text-xs text-oracle-muted">Twitter</p>
        </div>
      </div>

      {/* Social score bar */}
      <ScoreBar score={data.combined_score} label="Social Sentiment Score" />

      {/* Platform breakdown */}
      {(data.reddit.mentions > 0 || data.twitter.mentions > 0) && (
        <div className="space-y-2">
          {data.reddit.mentions > 0 && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-oracle-muted">Reddit</span>
              <div className="flex items-center gap-2">
                <span className="text-oracle-green">{data.reddit.positive_mentions} positive</span>
                <span className="text-oracle-muted">/</span>
                <span className="text-oracle-red">{data.reddit.negative_mentions} negative</span>
              </div>
            </div>
          )}
          {data.twitter.mentions > 0 && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-oracle-muted">Twitter</span>
              <div className="flex items-center gap-2">
                <span className="text-oracle-green">{data.twitter.positive_mentions} positive</span>
                <span className="text-oracle-muted">/</span>
                <span className="text-oracle-red">{data.twitter.negative_mentions} negative</span>
              </div>
            </div>
          )}
        </div>
      )}

      {data.total_mentions === 0 && (
        <p className="text-xs text-oracle-muted">No social mentions in the last 24h.</p>
      )}
    </div>
  );
}

export default function SentimentCard() {
  const [symbol, setSymbol] = useState("");
  const [data, setData] = useState<SentimentAnalysis | null>(null);
  const [socialData, setSocialData] = useState<SocialSentimentData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    const s = symbol.trim().toUpperCase();
    if (!s) return;

    setLoading(true);
    setError(null);
    setData(null);
    setSocialData(null);

    try {
      // Fetch AI sentiment and social sentiment in parallel
      const [aiResult, socialResult] = await Promise.allSettled([
        fetchAPI<SentimentAnalysis>(`/api/v1/market/sentiment/${s}`),
        fetchAPI<SocialSentimentData>(`/api/v1/market/social-sentiment/${s}`),
      ]);

      if (aiResult.status === "fulfilled") {
        setData(aiResult.value);
      }
      if (socialResult.status === "fulfilled") {
        setSocialData(socialResult.value);
      }

      if (aiResult.status === "rejected" && socialResult.status === "rejected") {
        setError("Failed to analyze sentiment");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to analyze sentiment");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide mb-3">
        Sentiment Analysis
      </h3>

      {/* Search input */}
      <div className="flex gap-2 mb-4">
        <SymbolAutocomplete
          value={symbol}
          onChange={setSymbol}
          onSubmit={(s) => { setSymbol(s); handleAnalyze(); }}
          placeholder="Enter symbol (e.g. AAPL)"
          className="flex-1"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading || !symbol.trim()}
          className="px-3 py-1.5 text-sm bg-oracle-accent/20 text-oracle-accent border border-oracle-accent/30 rounded hover:bg-oracle-accent/30 disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error && <p className="text-oracle-red text-sm mb-3">{error}</p>}

      {data && (
        <div className="space-y-4">
          {/* Symbol + Label */}
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold text-oracle-text">{data.symbol}</span>
            <div className="flex items-center gap-2">
              {socialData && socialData.buzz_level !== "none" && (
                <span
                  className={`px-2 py-0.5 text-xs font-medium uppercase rounded border ${BUZZ_COLORS[socialData.buzz_level]}`}
                >
                  {socialData.buzz_level} buzz
                </span>
              )}
              <span
                className={`px-2 py-0.5 text-xs font-medium uppercase rounded border ${LABEL_BG[data.label]}`}
              >
                <span className={LABEL_COLORS[data.label]}>{data.label}</span>
              </span>
            </div>
          </div>

          {/* AI Score bar */}
          <ScoreBar score={data.score} label="AI Sentiment Score" />

          {/* Narrative */}
          <p className="text-sm text-oracle-text leading-relaxed">
            {data.narrative}
          </p>

          {/* Key factors */}
          {data.key_factors.length > 0 && (
            <div>
              <p className="text-xs text-oracle-muted uppercase mb-1">
                Key Factors
              </p>
              <ul className="space-y-1">
                {data.key_factors.map((factor, i) => (
                  <li key={i} className="text-xs text-oracle-text flex gap-2">
                    <span className="text-oracle-accent shrink-0">*</span>
                    {factor}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Sources count */}
          {data.sources_count > 0 && (
            <p className="text-xs text-oracle-muted">
              Based on {data.sources_count} data points
            </p>
          )}
        </div>
      )}

      {/* Social Buzz Section — always shown when available */}
      {socialData && <SocialBuzzSection data={socialData} />}

      {!data && !socialData && !loading && !error && (
        <p className="text-oracle-muted text-sm">
          Enter a symbol to get AI sentiment + social media buzz analysis.
        </p>
      )}
    </div>
  );
}
