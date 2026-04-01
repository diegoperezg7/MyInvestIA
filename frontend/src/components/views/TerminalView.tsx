"use client";

import {
  startTransition,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  FileText,
  Gauge,
  Radar,
  RefreshCw,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { useView } from "@/contexts/ViewContext";
import { fetchAPI } from "@/lib/api";
import type {
  AnalyzedArticle,
  AssetQuote,
  EconomicCalendarResponse,
  EnhancedSentimentResponse,
  FilingsResponse,
  HistoricalData,
  InboxResponse,
  InboxItem,
  InsiderActivityResponse,
  MacroIntelligenceResponse,
  Portfolio,
  ResearchFactorResponse,
  TechnicalAnalysis,
  Thesis,
  ThesisListResponse,
  WatchlistList,
} from "@/types";
import SymbolAutocomplete from "@/components/ui/SymbolAutocomplete";
import Sparkline from "@/components/ui/Sparkline";
import useSparklines from "@/hooks/useSparklines";
import useCurrencyStore from "@/stores/useCurrencyStore";

const DEFAULT_SYMBOL = "NVDA";

function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(2)}T`;
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(2);
}

function formatDateLabel(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function toneClass(value: number): string {
  if (value > 0.2) return "text-oracle-green";
  if (value < -0.2) return "text-oracle-red";
  return "text-oracle-muted";
}

function badgeClass(value: number): string {
  if (value > 0.2) return "bg-oracle-green/15 text-oracle-green border-oracle-green/20";
  if (value < -0.2) return "bg-oracle-red/15 text-oracle-red border-oracle-red/20";
  return "bg-oracle-bg text-oracle-muted border-oracle-border";
}

function panelClass(extra = "") {
  return `rounded-xl border border-oracle-border bg-oracle-panel/95 backdrop-blur-sm ${extra}`.trim();
}

function TerminalPanel({
  title,
  subtitle,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={panelClass(className)}>
      <div className="flex items-start justify-between gap-3 border-b border-oracle-border px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
            {title}
          </p>
          {subtitle ? <p className="mt-1 text-xs text-oracle-muted">{subtitle}</p> : null}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function ScoreRail({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  const pct = ((Math.max(-1, Math.min(1, value)) + 1) / 2) * 100;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px] uppercase tracking-wide">
        <span className="text-oracle-muted">{label}</span>
        <span className={`font-mono ${toneClass(value)}`}>
          {value > 0 ? "+" : ""}
          {value.toFixed(2)}
        </span>
      </div>
      <div className="relative h-2 overflow-hidden rounded-full bg-oracle-bg">
        <div className="absolute inset-y-0 left-1/2 w-px bg-oracle-border" />
        <div
          className={`absolute top-0 h-full w-3 rounded-full ${value > 0.2 ? "bg-oracle-green" : value < -0.2 ? "bg-oracle-red" : "bg-oracle-accent"}`}
          style={{ left: `calc(${pct}% - 6px)` }}
        />
      </div>
    </div>
  );
}

function TapeItem({
  symbol,
  data,
}: {
  symbol: string;
  data: number[];
}) {
  const first = data[0] ?? 0;
  const last = data[data.length - 1] ?? 0;
  const delta = first ? ((last - first) / first) * 100 : 0;
  return (
    <div className="flex min-w-[132px] items-center gap-3 rounded-lg border border-oracle-border bg-oracle-bg/70 px-3 py-2">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-oracle-text">{symbol}</p>
        <p className={`text-xs font-mono ${delta >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
          {delta >= 0 ? "+" : ""}
          {delta.toFixed(2)}%
        </p>
      </div>
      <Sparkline data={data} width={60} height={22} />
    </div>
  );
}

function NewsWire({ articles }: { articles: AnalyzedArticle[] }) {
  if (articles.length === 0) {
    return <p className="text-sm text-oracle-muted">Todavía no hay flujo específico para este activo.</p>;
  }

  return (
    <div className="space-y-3">
      {articles.slice(0, 6).map((article) => (
        <a
          key={article.id}
          href={article.url}
          target="_blank"
          rel="noreferrer"
          className="block rounded-lg border border-oracle-border bg-oracle-bg/50 px-3 py-3 transition-colors hover:bg-oracle-bg"
        >
          <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] text-oracle-muted">
            <span>{article.source}</span>
            <span className={`rounded border px-1.5 py-0.5 ${badgeClass(article.sentiment_score)}`}>
              {article.sentiment_score > 0.15 ? "positivo" : article.sentiment_score < -0.15 ? "negativo" : "neutral"}
            </span>
            <span className="ml-auto font-mono">
              {(article.source_reliability * 100).toFixed(0)} fiabilidad
            </span>
          </div>
          <p className="text-sm font-medium leading-5 text-oracle-text">{article.headline}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-oracle-muted">
            {article.ticker_mentions.slice(0, 3).map((ticker) => (
              <span
                key={`${article.id}-${ticker}`}
                className="rounded bg-oracle-accent/10 px-1.5 py-0.5 font-mono text-oracle-accent"
              >
                {ticker}
              </span>
            ))}
            <span>fiabilidad {(article.confidence * 100).toFixed(0)}%</span>
            <span>{article.retrieval_mode.replace("_", " ")}</span>
          </div>
        </a>
      ))}
    </div>
  );
}

export default function TerminalView() {
  const { selectedSymbol, setSelectedSymbol } = useView();
  const { formatPrice } = useCurrencyStore();
  const [inputSymbol, setInputSymbol] = useState(selectedSymbol || DEFAULT_SYMBOL);
  const [workspaceSymbol, setWorkspaceSymbol] = useState(selectedSymbol || DEFAULT_SYMBOL);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [quote, setQuote] = useState<AssetQuote | null>(null);
  const [history, setHistory] = useState<HistoricalData | null>(null);
  const [technical, setTechnical] = useState<TechnicalAnalysis | null>(null);
  const [sentiment, setSentiment] = useState<EnhancedSentimentResponse | null>(null);
  const [news, setNews] = useState<AnalyzedArticle[]>([]);
  const [macro, setMacro] = useState<MacroIntelligenceResponse | null>(null);
  const [calendar, setCalendar] = useState<EconomicCalendarResponse | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watchlists, setWatchlists] = useState<WatchlistList | null>(null);
  const [filings, setFilings] = useState<FilingsResponse | null>(null);
  const [insiders, setInsiders] = useState<InsiderActivityResponse | null>(null);
  const [decisionInbox, setDecisionInbox] = useState<InboxItem[]>([]);
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [researchFactors, setResearchFactors] = useState<ResearchFactorResponse | null>(null);

  useEffect(() => {
    if (selectedSymbol) {
      setInputSymbol(selectedSymbol);
      setWorkspaceSymbol(selectedSymbol);
    }
  }, [selectedSymbol]);

  const loadWorkspace = useCallback(async (symbol: string, skipCache = false) => {
    const target = symbol.trim().toUpperCase() || DEFAULT_SYMBOL;
    setLoading(true);
    setError(null);

    const results = await Promise.allSettled([
      fetchAPI<AssetQuote>(`/api/v1/market/quote/${target}`, { skipCache }),
      fetchAPI<HistoricalData>(`/api/v1/market/history/${target}?period=6mo&interval=1d`, { skipCache }),
      fetchAPI<TechnicalAnalysis>(`/api/v1/market/analysis/${target}?period=6mo`, { skipCache }),
      fetchAPI<EnhancedSentimentResponse>(`/api/v1/market/enhanced-sentiment/${target}`, { skipCache }),
      fetchAPI<{ articles: AnalyzedArticle[] }>(`/api/v1/news/feed`, { skipCache }),
      fetchAPI<MacroIntelligenceResponse>(`/api/v1/market/macro`, { skipCache }),
      fetchAPI<EconomicCalendarResponse>(`/api/v1/market/calendar`, { skipCache }),
      fetchAPI<Portfolio>(`/api/v1/portfolio/`, { skipCache }),
      fetchAPI<WatchlistList>(`/api/v1/watchlists/`, { skipCache }),
      fetchAPI<FilingsResponse>(`/api/v1/market/filings/${target}`, { skipCache }),
      fetchAPI<InsiderActivityResponse>(`/api/v1/market/insiders/${target}`, { skipCache }),
      fetchAPI<InboxResponse>(`/api/v1/inbox?symbol=${target}`, { skipCache }),
      fetchAPI<ThesisListResponse>(`/api/v1/theses?symbol=${target}`, { skipCache }),
      fetchAPI<ResearchFactorResponse>(`/api/v1/research/factors/${target}`, { skipCache }),
    ]);

    const failures = results.filter((result) => result.status === "rejected").length;
    if (failures === results.length) {
      setError("No se pudo cargar el workspace terminal.");
    }

    setQuote(results[0].status === "fulfilled" ? results[0].value : null);
    setHistory(results[1].status === "fulfilled" ? results[1].value : null);
    setTechnical(results[2].status === "fulfilled" ? results[2].value : null);
    setSentiment(results[3].status === "fulfilled" ? results[3].value : null);
    setNews(results[4].status === "fulfilled" ? results[4].value.articles ?? [] : []);
    setMacro(results[5].status === "fulfilled" ? results[5].value : null);
    setCalendar(results[6].status === "fulfilled" ? results[6].value : null);
    setPortfolio(results[7].status === "fulfilled" ? results[7].value : null);
    setWatchlists(results[8].status === "fulfilled" ? results[8].value : null);
    setFilings(results[9].status === "fulfilled" ? results[9].value : null);
    setInsiders(results[10].status === "fulfilled" ? results[10].value : null);
    setDecisionInbox(results[11].status === "fulfilled" ? results[11].value.items ?? [] : []);
    setTheses(results[12].status === "fulfilled" ? results[12].value.theses ?? [] : []);
    setResearchFactors(results[13].status === "fulfilled" ? results[13].value : null);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadWorkspace(workspaceSymbol);
  }, [loadWorkspace, workspaceSymbol]);

  const workspaceSymbols = useMemo(() => {
    const symbols = new Set<string>([workspaceSymbol]);
    portfolio?.holdings.slice(0, 5).forEach((holding) => symbols.add(holding.asset.symbol));
    watchlists?.watchlists.slice(0, 2).forEach((watchlist) => {
      watchlist.assets.slice(0, 4).forEach((asset) => symbols.add(asset.symbol));
    });
    return Array.from(symbols).slice(0, 12);
  }, [portfolio, watchlists, workspaceSymbol]);

  const sparklines = useSparklines(workspaceSymbols);

  const wireArticles = useMemo(() => {
    const symbolMatches = news.filter((article) => article.ticker_mentions.includes(workspaceSymbol));
    return (symbolMatches.length > 0 ? symbolMatches : news).slice(0, 8);
  }, [news, workspaceSymbol]);

  const chartData = useMemo(
    () =>
      history?.data.map((point) => ({
        date: formatDateLabel(point.date),
        close: point.close,
        volume: point.volume,
      })) ?? [],
    [history]
  );

  const holdings = portfolio?.holdings ?? [];
  const watchAssets = watchlists?.watchlists.flatMap((watchlist) => watchlist.assets) ?? [];
  const fearGreed = macro?.fear_greed;

  return (
    <div className="space-y-4">
      <section className="oracle-hero-surface rounded-2xl border border-oracle-border">
        <div className="grid gap-5 px-4 py-5 lg:grid-cols-[1.25fr_0.75fr] lg:px-5">
          <div>
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <span className="rounded-full border border-oracle-accent/30 bg-oracle-accent/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-oracle-accent">
                Detalle del activo
              </span>
              <span className="text-xs text-oracle-muted">
                Precio, noticias, sentimiento, filings y contexto del activo
              </span>
            </div>
            <div className="flex flex-col gap-3 md:flex-row">
              <SymbolAutocomplete
                value={inputSymbol}
                onChange={setInputSymbol}
                onSubmit={(symbol) => {
                  const next = symbol.trim().toUpperCase();
                  startTransition(() => {
                    setInputSymbol(next);
                    setWorkspaceSymbol(next);
                    setSelectedSymbol(next);
                  });
                }}
                placeholder="Símbolo o ETF (AAPL, NVDA, BTC)"
                className="flex-1"
              />
              <button
                onClick={() => loadWorkspace(workspaceSymbol, true)}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-oracle-accent/30 bg-oracle-accent/15 px-4 py-2 text-sm font-medium text-oracle-accent transition-colors hover:bg-oracle-accent/25"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                Actualizar
              </button>
            </div>
            {error ? <p className="mt-3 text-sm text-oracle-red">{error}</p> : null}
            <div className="mt-4 flex flex-wrap gap-2">
              {workspaceSymbols.map((symbol) => (
                <button
                  key={symbol}
                  onClick={() => {
                    startTransition(() => {
                      setInputSymbol(symbol);
                      setWorkspaceSymbol(symbol);
                      setSelectedSymbol(symbol);
                    });
                  }}
                  className={`rounded-md border px-2.5 py-1 text-xs font-mono transition-colors ${
                    symbol === workspaceSymbol
                      ? "border-oracle-accent/40 bg-oracle-accent/20 text-oracle-accent"
                      : "border-oracle-border bg-oracle-bg/50 text-oracle-muted hover:text-oracle-text"
                  }`}
                >
                  {symbol}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
            <div className={panelClass("px-3 py-3")}>
              <p className="text-[10px] uppercase tracking-[0.22em] text-oracle-muted">Último precio</p>
              <p className="mt-2 text-xl font-bold text-oracle-text">
                {quote ? formatPrice(quote.price) : "--"}
              </p>
              <p className={`mt-1 text-xs font-mono ${quote && quote.change_percent >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                {quote ? `${quote.change_percent >= 0 ? "+" : ""}${quote.change_percent.toFixed(2)}%` : "--"}
              </p>
            </div>
            <div className={panelClass("px-3 py-3")}>
              <p className="text-[10px] uppercase tracking-[0.22em] text-oracle-muted">Señal general</p>
              <p className={`mt-2 text-xl font-bold ${sentiment ? toneClass(sentiment.unified_score) : "text-oracle-text"}`}>
                {sentiment ? `${sentiment.unified_score > 0 ? "+" : ""}${sentiment.unified_score.toFixed(2)}` : "--"}
              </p>
              <p className="mt-1 text-xs uppercase text-oracle-muted">{sentiment?.unified_label ?? "neutral"}</p>
            </div>
            <div className={panelClass("px-3 py-3")}>
              <p className="text-[10px] uppercase tracking-[0.22em] text-oracle-muted">Calidad de datos</p>
              <p className="mt-2 text-xl font-bold text-oracle-text">
                {sentiment ? `${(sentiment.coverage_confidence * 100).toFixed(0)}%` : "--"}
              </p>
              <p className="mt-1 text-xs text-oracle-muted">{sentiment?.total_data_points ?? 0} puntos de datos</p>
            </div>
            <div className={panelClass("px-3 py-3")}>
              <p className="text-[10px] uppercase tracking-[0.22em] text-oracle-muted">Fear & Greed</p>
              <p className="mt-2 text-xl font-bold text-oracle-text">{fearGreed?.value ?? "--"}</p>
              <p className="mt-1 text-xs text-oracle-muted">{fearGreed?.classification ?? "n/a"}</p>
            </div>
            <div className={panelClass("px-3 py-3")}>
              <p className="text-[10px] uppercase tracking-[0.22em] text-oracle-muted">Volumen</p>
              <p className="mt-2 text-xl font-bold text-oracle-text">
                {quote ? formatCompact(quote.volume) : "--"}
              </p>
              <p className="mt-1 text-xs text-oracle-muted">cotización en vivo</p>
            </div>
            <div className={panelClass("px-3 py-3")}>
              <p className="text-[10px] uppercase tracking-[0.22em] text-oracle-muted">Fuentes</p>
              <p className="mt-2 text-xl font-bold text-oracle-text">
                {sentiment?.source_breakdown.length ?? 0}
              </p>
              <p className="mt-1 text-xs text-oracle-muted">fuentes activas</p>
            </div>
          </div>
        </div>
      </section>

      <section className="overflow-x-auto">
        <div className="flex gap-3 pb-1">
          {workspaceSymbols.map((symbol) => (
            <TapeItem key={symbol} symbol={symbol} data={sparklines[symbol] ?? []} />
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="space-y-4 xl:col-span-8">
          <div className="grid gap-4 lg:grid-cols-[1.6fr_0.9fr]">
            <TerminalPanel title={`${workspaceSymbol} · Precio y contexto`} subtitle="Seis meses de precio y volumen para entender el fondo">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <div>
                  <p className="text-lg font-bold text-oracle-text">{quote?.name ?? workspaceSymbol}</p>
                  <p className="text-xs text-oracle-muted">{workspaceSymbol}</p>
                </div>
                <div className="ml-auto flex items-center gap-3 text-xs text-oracle-muted">
                  <span>Cierre previo {quote ? formatPrice(quote.previous_close) : "--"}</span>
                  <span>Capitalización {quote?.market_cap ? formatCompact(quote.market_cap) : "--"}</span>
                </div>
              </div>
              <div className="h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="terminalChartFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#38bdf8" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fill: "var(--color-oracle-muted)", fontSize: 11 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fill: "var(--color-oracle-muted)", fontSize: 11 }} tickLine={false} axisLine={false} domain={["auto", "auto"]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "rgba(17,24,39,0.96)",
                        border: "1px solid rgba(148,163,184,0.2)",
                        borderRadius: "0.75rem",
                      }}
                    />
                    <Area type="monotone" dataKey="close" stroke="#38bdf8" strokeWidth={2} fill="url(#terminalChartFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </TerminalPanel>

            <TerminalPanel title="Lectura rápida" subtitle="Señales técnicas y confirmación en una sola vista">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-lg border border-oracle-border bg-oracle-bg/50 p-3">
                    <p className="text-[11px] uppercase tracking-wide text-oracle-muted">RSI</p>
                    <p className="mt-2 text-xl font-bold text-oracle-text">
                      {technical?.rsi.value !== null && technical?.rsi.value !== undefined ? technical.rsi.value.toFixed(1) : "--"}
                    </p>
                    <p className={`mt-1 text-xs uppercase ${technical ? toneClass(technical.rsi.signal === "bullish" ? 1 : technical.rsi.signal === "bearish" ? -1 : 0) : "text-oracle-muted"}`}>
                      {technical?.rsi.signal ?? "neutral"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-oracle-border bg-oracle-bg/50 p-3">
                    <p className="text-[11px] uppercase tracking-wide text-oracle-muted">MACD</p>
                    <p className="mt-2 text-xl font-bold text-oracle-text">
                      {technical?.macd.histogram !== null && technical?.macd.histogram !== undefined ? technical.macd.histogram.toFixed(2) : "--"}
                    </p>
                    <p className={`mt-1 text-xs uppercase ${technical ? toneClass(technical.macd.signal === "bullish" ? 1 : technical.macd.signal === "bearish" ? -1 : 0) : "text-oracle-muted"}`}>
                      {technical?.macd.signal ?? "neutral"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-oracle-border bg-oracle-bg/50 p-3">
                    <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Tendencia</p>
                    <p className="mt-2 text-xl font-bold text-oracle-text">{technical?.overall_signal ?? "--"}</p>
                    <p className="mt-1 text-xs text-oracle-muted">
                      alcista {technical?.signal_counts.bullish ?? 0} / bajista {technical?.signal_counts.bearish ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg border border-oracle-border bg-oracle-bg/50 p-3">
                    <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Bandas</p>
                    <p className="mt-2 text-xl font-bold text-oracle-text">
                      {technical?.bollinger_bands.bandwidth !== null && technical?.bollinger_bands.bandwidth !== undefined ? technical.bollinger_bands.bandwidth.toFixed(2) : "--"}
                    </p>
                    <p className="mt-1 text-xs uppercase text-oracle-muted">{technical?.bollinger_bands.signal ?? "neutral"}</p>
                  </div>
                </div>
                <ScoreRail label="Impulso en noticias" value={sentiment?.news_momentum ?? 0} />
                <ScoreRail label="Impulso en redes" value={sentiment?.social_momentum ?? 0} />
                <ScoreRail label="Desacuerdo entre fuentes" value={-(sentiment?.cross_source_divergence ?? 0)} />
              </div>
            </TerminalPanel>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
            <TerminalPanel title="Flujo relevante" subtitle="Noticias y señales ponderadas por fiabilidad">
              <NewsWire articles={wireArticles} />
            </TerminalPanel>

            <TerminalPanel title="Pulso macro y eventos" subtitle="Series oficiales, miedo y codicia y próximos catalizadores">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-oracle-border bg-oracle-bg/60 p-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-oracle-muted">
                      <Gauge className="h-3.5 w-3.5" />
                      Entorno
                    </div>
                    <p className="mt-2 text-lg font-semibold text-oracle-text">{macro?.summary.environment ?? "--"}</p>
                    <p className="text-xs text-oracle-muted">{macro?.summary.risk_level ?? "desconocido"} riesgo</p>
                  </div>
                  <div className="rounded-lg border border-oracle-border bg-oracle-bg/60 p-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-oracle-muted">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      Fear / Greed
                    </div>
                    <p className="mt-2 text-lg font-semibold text-oracle-text">{fearGreed?.value ?? "--"}</p>
                    <p className="text-xs text-oracle-muted">{fearGreed?.classification ?? "n/a"}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  {(macro?.official_series ?? []).slice(0, 4).map((series) => (
                    <div
                      key={series.id}
                      className="flex items-center justify-between rounded-lg border border-oracle-border bg-oracle-bg/45 px-3 py-2 text-sm"
                    >
                      <div>
                        <p className="font-medium text-oracle-text">{series.name}</p>
                        <p className="text-xs text-oracle-muted">{series.source} · {series.date}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-oracle-text">{series.value ?? "--"} {series.unit}</p>
                        <p className={`text-xs font-mono ${series.change_percent >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                          {series.change_percent >= 0 ? "+" : ""}
                          {series.change_percent.toFixed(2)}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="space-y-2">
                  {(calendar?.events ?? []).slice(0, 4).map((event, index) => (
                    <div key={`${event.date}-${event.event}-${index}`} className="rounded-lg border border-oracle-border bg-oracle-bg/45 px-3 py-2">
                      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-oracle-muted">
                        <span>{event.date}</span>
                        <span className="rounded border border-oracle-border px-1.5 py-0.5">{event.impact}</span>
                      </div>
                      <p className="mt-1 text-sm font-medium text-oracle-text">{event.event}</p>
                    </div>
                  ))}
                </div>
              </div>
            </TerminalPanel>
          </div>
        </div>

        <div className="space-y-4 xl:col-span-4">
          <TerminalPanel title="Cartera y seguimiento" subtitle="Activos más cercanos al símbolo que estás revisando">
            <div className="space-y-3">
              {holdings.slice(0, 4).map((holding) => (
                <div key={holding.asset.symbol} className="flex items-center gap-3 rounded-lg border border-oracle-border bg-oracle-bg/50 px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-oracle-text">{holding.asset.symbol}</p>
                    <p className="text-xs text-oracle-muted">{holding.quantity.toFixed(2)} acciones</p>
                  </div>
                  <Sparkline data={sparklines[holding.asset.symbol] ?? []} width={64} height={24} />
                  <div className="text-right">
                    <p className="font-mono text-sm text-oracle-text">{formatPrice(holding.current_value)}</p>
                    <p className={`text-xs font-mono ${holding.unrealized_pnl >= 0 ? "text-oracle-green" : "text-oracle-red"}`}>
                      {holding.unrealized_pnl >= 0 ? "+" : ""}
                      {formatPrice(holding.unrealized_pnl)}
                    </p>
                  </div>
                </div>
              ))}
              {holdings.length === 0 ? <p className="text-sm text-oracle-muted">No hay posiciones cargadas.</p> : null}
              <div className="grid grid-cols-2 gap-2 pt-1">
                {watchAssets.slice(0, 6).map((asset) => (
                  <button
                    key={asset.symbol}
                    onClick={() => {
                      startTransition(() => {
                        setInputSymbol(asset.symbol);
                        setWorkspaceSymbol(asset.symbol);
                        setSelectedSymbol(asset.symbol);
                      });
                    }}
                    className="rounded-lg border border-oracle-border bg-oracle-bg/45 px-3 py-2 text-left transition-colors hover:bg-oracle-bg"
                  >
                    <p className="font-mono text-sm text-oracle-text">{asset.symbol}</p>
                    <p className="mt-1 text-xs text-oracle-muted">{asset.name}</p>
                  </button>
                ))}
              </div>
            </div>
          </TerminalPanel>

          <TerminalPanel title="Contexto de decisión" subtitle="Prioridad, tesis y lectura cuantitativa para este activo">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-oracle-border bg-oracle-bg/60 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Prioridad</p>
                  <p className="mt-2 text-xl font-semibold text-oracle-text">
                    {decisionInbox[0] ? decisionInbox[0].priority_score.toFixed(0) : "--"}
                  </p>
                  <p className="text-xs text-oracle-muted">{decisionInbox[0]?.state ?? "sin item"}</p>
                </div>
                <div className="rounded-lg border border-oracle-border bg-oracle-bg/60 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Tesis</p>
                  <p className="mt-2 text-xl font-semibold text-oracle-text">
                    {theses[0]?.review_state ?? "--"}
                  </p>
                  <p className="text-xs text-oracle-muted">{theses[0]?.stance ?? "sin tesis"}</p>
                </div>
              </div>

              {decisionInbox[0] ? (
                <div className="rounded-lg border border-oracle-border bg-oracle-bg/45 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Lo más importante ahora</p>
                  <p className="mt-2 text-sm font-medium text-oracle-text">{decisionInbox[0].title}</p>
                  <p className="mt-1 text-xs leading-5 text-oracle-muted">
                    {decisionInbox[0].why_now || decisionInbox[0].summary}
                  </p>
                </div>
              ) : null}

              {theses[0] ? (
                <div className="rounded-lg border border-oracle-border bg-oracle-bg/45 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Tesis activa</p>
                  <p className="mt-2 text-sm font-medium text-oracle-text">
                    {theses[0].stance} · {Math.round(theses[0].conviction * 100)}% convicción
                  </p>
                  <p className="mt-1 text-xs leading-5 text-oracle-muted">{theses[0].notes || "Sin notas todavía."}</p>
                </div>
              ) : null}

              {researchFactors ? (
                <div className="rounded-lg border border-oracle-border bg-oracle-bg/45 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Resumen cuantitativo</p>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                    <div className="rounded-lg border border-oracle-border bg-oracle-panel/60 px-2 py-2">
                      <p className="text-oracle-muted">Puntuación</p>
                      <p className="mt-1 font-mono text-oracle-text">{researchFactors.composite_score.toFixed(1)}</p>
                    </div>
                    <div className="rounded-lg border border-oracle-border bg-oracle-panel/60 px-2 py-2">
                      <p className="text-oracle-muted">Impulso</p>
                      <p className="mt-1 font-mono text-oracle-text">{researchFactors.factors.momentum.toFixed(0)}</p>
                    </div>
                    <div className="rounded-lg border border-oracle-border bg-oracle-panel/60 px-2 py-2">
                      <p className="text-oracle-muted">Risk</p>
                      <p className="mt-1 font-mono text-oracle-text">{researchFactors.factors.risk.toFixed(0)}</p>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </TerminalPanel>

          <TerminalPanel title="Pulso de sentimiento" subtitle="Narrativas y equilibrio entre fuentes para este activo">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-oracle-border bg-oracle-bg/60 p-3">
                  <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-oracle-muted">
                    <Radar className="h-3.5 w-3.5" />
                    General
                  </div>
                  <p className={`mt-2 text-lg font-semibold ${toneClass(sentiment?.unified_score ?? 0)}`}>
                    {sentiment ? `${sentiment.unified_score > 0 ? "+" : ""}${sentiment.unified_score.toFixed(2)}` : "--"}
                  </p>
                  <p className="text-xs text-oracle-muted">{sentiment?.unified_label ?? "neutral"}</p>
                </div>
                <div className="rounded-lg border border-oracle-border bg-oracle-bg/60 p-3">
                  <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-oracle-muted">
                    <Activity className="h-3.5 w-3.5" />
                    Calidad de datos
                  </div>
                  <p className="mt-2 text-lg font-semibold text-oracle-text">
                    {sentiment ? `${(sentiment.coverage_confidence * 100).toFixed(0)}%` : "--"}
                  </p>
                  <p className="text-xs text-oracle-muted">{sentiment?.source_breakdown.length ?? 0} fuentes</p>
                </div>
              </div>

              <div className="space-y-2">
                {(sentiment?.top_narratives ?? []).map((narrative) => (
                  <div key={narrative.label} className="rounded-lg border border-oracle-border bg-oracle-bg/45 px-3 py-2">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-oracle-text">{narrative.label}</p>
                      <span className={`text-xs font-mono ${toneClass(narrative.avg_sentiment)}`}>
                        {narrative.avg_sentiment > 0 ? "+" : ""}
                        {narrative.avg_sentiment.toFixed(2)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-oracle-muted">
                      {narrative.mentions} menciones
                      {narrative.symbols.length > 0 ? ` · ${narrative.symbols.join(", ")}` : ""}
                    </p>
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                {(sentiment?.source_breakdown ?? []).slice(0, 4).map((item) => (
                  <div key={item.provider} className="flex items-center justify-between rounded-lg border border-oracle-border bg-oracle-bg/45 px-3 py-2 text-sm">
                    <div>
                      <p className="font-medium text-oracle-text">{item.provider}</p>
                      <p className="text-xs text-oracle-muted">{item.count} items · {item.retrieval_mode}</p>
                    </div>
                    <div className="text-right">
                      <p className={`font-mono ${toneClass(item.avg_sentiment)}`}>
                        {item.avg_sentiment > 0 ? "+" : ""}
                        {item.avg_sentiment.toFixed(2)}
                      </p>
                      <p className="text-xs text-oracle-muted">{(item.avg_confidence * 100).toFixed(0)} fiabilidad</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </TerminalPanel>

          <TerminalPanel title="Filings SEC" subtitle="Flujo reciente de EDGAR para este activo">
            <div className="space-y-2">
              {(filings?.filings ?? []).slice(0, 5).map((filing) => (
                <a
                  key={filing.accession_number}
                  href={filing.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-start gap-3 rounded-lg border border-oracle-border bg-oracle-bg/45 px-3 py-2 transition-colors hover:bg-oracle-bg"
                >
                  <FileText className="mt-0.5 h-4 w-4 text-oracle-accent" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm text-oracle-text">{filing.form}</span>
                      <span className="text-xs text-oracle-muted">{filing.filed_at}</span>
                    </div>
                    <p className="mt-1 text-sm text-oracle-text">{filing.description || filing.form}</p>
                  </div>
                </a>
              ))}
              {(filings?.filings ?? []).length === 0 ? <p className="text-sm text-oracle-muted">No han aparecido filings recientes.</p> : null}
            </div>
          </TerminalPanel>

          <TerminalPanel title="Actividad interna" subtitle="Alpha Vantage si está disponible y SEC como respaldo">
            <div className="space-y-2">
              {(insiders?.transactions ?? []).slice(0, 5).map((txn, index) => (
                <div key={`${txn.filing_date}-${txn.transaction_type}-${index}`} className="flex items-start gap-3 rounded-lg border border-oracle-border bg-oracle-bg/45 px-3 py-2">
                  <UserRound className="mt-0.5 h-4 w-4 text-oracle-muted" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-oracle-text">{txn.insider_name || txn.transaction_type}</p>
                      <span className="text-xs text-oracle-muted">{txn.filing_date}</span>
                    </div>
                    <p className="mt-1 text-xs text-oracle-muted">
                      {txn.relation || txn.source} · {txn.transaction_type}
                    </p>
                    <p className="mt-1 text-xs font-mono text-oracle-text">
                      {txn.shares ? `${formatCompact(txn.shares)} acc. @ ${txn.share_price.toFixed(2)}` : "Actividad registrada en formularios"}
                    </p>
                  </div>
                </div>
              ))}
              {(insiders?.transactions ?? []).length === 0 ? <p className="text-sm text-oracle-muted">No se ha devuelto actividad interna reciente.</p> : null}
            </div>
          </TerminalPanel>
        </div>
      </div>
    </div>
  );
}
