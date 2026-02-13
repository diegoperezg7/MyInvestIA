"use client";

import { useState } from "react";
import { useNewsFeed } from "@/hooks/useNewsFeed";
import useLanguageStore from "@/stores/useLanguageStore";
import type { AnalyzedArticle } from "@/types";
import {
  RefreshCw,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const SOURCE_COLORS: Record<string, string> = {
  finnhub: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  newsapi: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  rss: "bg-orange-500/20 text-orange-400 border-orange-500/30",
};

const SENTIMENT_ICON: Record<string, React.ElementType> = {
  positive: TrendingUp,
  negative: TrendingDown,
  neutral: Minus,
};

const SENTIMENT_COLOR: Record<string, string> = {
  positive: "text-oracle-green",
  negative: "text-oracle-red",
  neutral: "text-oracle-muted",
};

function timeAgo(ts: number, nowLabel: string): string {
  const diff = Date.now() / 1000 - ts;
  const mins = Math.floor(diff / 60);
  if (mins < 1) return nowLabel;
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

function ImpactMeter({ score, label }: { score: number; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-oracle-muted">{label}</span>
      <div className="flex-1 h-1.5 bg-oracle-bg rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            score >= 7
              ? "bg-oracle-red"
              : score >= 4
                ? "bg-oracle-yellow"
                : "bg-oracle-green"
          }`}
          style={{ width: `${score * 10}%` }}
        />
      </div>
      <span className="text-xs font-mono text-oracle-text">{score}/10</span>
    </div>
  );
}

function ArticleItem({ article, t }: { article: AnalyzedArticle; t: (key: string, params?: Record<string, string>) => string }) {
  const [expanded, setExpanded] = useState(false);
  const analysis = article.ai_analysis;
  const urgency = analysis?.urgency || "normal";

  const SentimentIcon = analysis
    ? SENTIMENT_ICON[analysis.sentiment] || Minus
    : Minus;

  return (
    <div
      className="border-b border-oracle-border last:border-b-0 py-2.5 cursor-pointer hover:bg-oracle-bg/50 px-2 -mx-2 rounded transition-colors"
      onClick={() => setExpanded(!expanded)}
    >
      {/* Main row */}
      <div className="flex items-start gap-2">
        {/* Urgency dot */}
        <div className="mt-1.5 shrink-0">
          {urgency === "breaking" ? (
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-oracle-red opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-oracle-red" />
            </span>
          ) : urgency === "high" ? (
            <span className="inline-flex rounded-full h-2.5 w-2.5 bg-oracle-yellow" />
          ) : (
            <span className="inline-flex rounded-full h-2.5 w-2.5 bg-transparent" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-oracle-text truncate">{article.headline}</p>
          <div className="flex items-center gap-2 mt-1">
            {/* Source badge */}
            <span
              className={`text-xs px-1.5 py-0.5 rounded border ${
                SOURCE_COLORS[article.source_provider] ||
                "bg-oracle-bg text-oracle-muted border-oracle-border"
              }`}
            >
              {article.source}
            </span>
            {/* Tickers */}
            {analysis?.affected_tickers?.slice(0, 3).map((tk) => (
              <span
                key={tk}
                className="text-xs font-mono px-1 py-0.5 bg-oracle-accent/10 text-oracle-accent rounded"
              >
                {tk}
              </span>
            ))}
            {/* Timestamp */}
            <span className="text-xs text-oracle-muted ml-auto shrink-0">
              {timeAgo(article.datetime, t("news.now"))}
            </span>
          </div>
        </div>

        {/* Sentiment indicator */}
        <div className="shrink-0 mt-0.5">
          <SentimentIcon
            className={`w-4 h-4 ${
              analysis ? SENTIMENT_COLOR[analysis.sentiment] : "text-oracle-muted"
            }`}
          />
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-3 ml-5 space-y-2">
          {article.summary && (
            <p className="text-xs text-oracle-muted leading-relaxed">
              {article.summary}
            </p>
          )}
          {analysis && (
            <>
              <p className="text-xs text-oracle-text">{analysis.brief_analysis}</p>
              <ImpactMeter score={analysis.impact_score} label={t("news.impact")} />
              {analysis.affected_tickers.length > 0 && (
                <div className="flex items-center gap-1 flex-wrap">
                  <span className="text-xs text-oracle-muted">{t("news.affected_tickers")}</span>
                  {analysis.affected_tickers.map((tk) => (
                    <span
                      key={tk}
                      className="text-xs font-mono px-1.5 py-0.5 bg-oracle-bg border border-oracle-border rounded text-oracle-text"
                    >
                      {tk}
                    </span>
                  ))}
                </div>
              )}
            </>
          )}
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-oracle-accent hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {t("news.open_article")} <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export default function BreakingNewsFeed({ defaultCollapsed = true, className = "" }: { defaultCollapsed?: boolean; className?: string }) {
  const { articles, loading, error, refresh } = useNewsFeed();
  const [showAll, setShowAll] = useState(false);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const t = useLanguageStore((s) => s.t);

  const VISIBLE_COUNT = 3;
  const displayed = showAll ? articles : articles.slice(0, VISIBLE_COUNT);

  return (
    <div className={`bg-oracle-panel border border-oracle-border rounded-lg p-4 flex flex-col ${className}`}>
      {/* Collapsible header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 flex-1"
        >
          <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
            {t("news.title")}
          </h3>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-oracle-green opacity-50" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-oracle-green" />
          </span>
          {articles.length > 0 && (
            <span className="text-oracle-muted text-xs">
              {t("news.articles_count", { count: String(articles.length) })}
            </span>
          )}
          {collapsed
            ? <ChevronDown className="w-3.5 h-3.5 text-oracle-muted" />
            : <ChevronUp className="w-3.5 h-3.5 text-oracle-muted" />
          }
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); refresh(); }}
          disabled={loading}
          className="p-1 rounded text-oracle-muted hover:text-oracle-accent hover:bg-oracle-bg transition-colors disabled:opacity-50"
          title={t("news.refresh")}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && <p className="text-oracle-red text-xs mt-2">{error}</p>}

      {/* Collapsible content */}
      {!collapsed && (
        <div className="mt-3 flex-1 overflow-y-auto">
          {/* Loading */}
          {loading && articles.length === 0 && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="w-full h-4 rounded bg-oracle-bg mb-1" />
                  <div className="w-2/3 h-3 rounded bg-oracle-bg" />
                </div>
              ))}
            </div>
          )}

          {/* Articles list */}
          {displayed.length > 0 && (
            <div>
              {displayed.map((article) => (
                <ArticleItem key={article.id} article={article} t={t} />
              ))}
            </div>
          )}

          {/* Show more */}
          {articles.length > VISIBLE_COUNT && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="w-full mt-2 py-1.5 text-xs text-oracle-accent hover:bg-oracle-bg rounded transition-colors flex items-center justify-center gap-1"
            >
              {showAll ? (
                <>
                  {t("news.show_less")} <ChevronUp className="w-3 h-3" />
                </>
              ) : (
                <>
                  {t("news.show_more", { count: String(articles.length - VISIBLE_COUNT) })} <ChevronDown className="w-3 h-3" />
                </>
              )}
            </button>
          )}

          {!loading && articles.length === 0 && !error && (
            <p className="text-oracle-muted text-sm text-center py-4">
              {t("news.no_news")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
