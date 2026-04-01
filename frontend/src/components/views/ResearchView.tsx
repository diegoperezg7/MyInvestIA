"use client";

import { useMemo, useState } from "react";
import { BarChart3, BookmarkPlus, Database, RefreshCw, Sigma } from "lucide-react";

import AnalysisView from "@/components/views/AnalysisView";
import PredictionView from "@/components/views/PredictionView";
import ScreenerView from "@/components/views/ScreenerView";
import SectionWorkspace from "@/components/layout/SectionWorkspace";
import { useResearch } from "@/hooks/useResearch";
import { useView } from "@/contexts/ViewContext";
import { getConfidenceBand, getInboxKindLabel } from "@/lib/presentation";
import { SECTION_TABS, getSectionDescription } from "@/lib/shell";
import useLanguageStore from "@/stores/useLanguageStore";

function factorColor(value: number) {
  if (value >= 70) return "text-oracle-green";
  if (value <= 40) return "text-oracle-red";
  return "text-oracle-yellow";
}

export default function ResearchView() {
  const { rankings, factors, snapshots, loading, error, selectedSymbol, setSelectedSymbol, loadRankings, saveScreen } = useResearch();
  const { activeTab, openAssetDetail, setActiveSection, setSelectedSymbol: setGlobalSymbol } = useView();
  const language = useLanguageStore((state) => state.language);
  const [screenName, setScreenName] = useState("Core Research");
  const currentTab = activeTab.startsWith("research-")
    ? activeTab
    : "research-ideas";

  const topSymbols = useMemo(
    () => rankings?.rankings.slice(0, 8).map((entry) => entry.symbol) ?? [],
    [rankings]
  );

  if (currentTab === "research-screener") {
    return (
      <SectionWorkspace
        eyebrow={language === "es" ? "Investigación" : "Research"}
        title={language === "es" ? "Explora ideas con una estructura más clara" : "Explore ideas with a clearer structure"}
        description={getSectionDescription("research", language)}
        tabs={SECTION_TABS.research.map((tab) => ({
          id: tab.id,
          label: tab.label[language],
          hint: tab.description?.[language],
        }))}
        activeTab={currentTab}
        onTabChange={(tab) => setActiveSection("research", tab)}
      >
        <ScreenerView />
      </SectionWorkspace>
    );
  }

  if (currentTab === "research-factors") {
    return (
      <SectionWorkspace
        eyebrow={language === "es" ? "Investigación" : "Research"}
        title={language === "es" ? "Explora ideas con una estructura más clara" : "Explore ideas with a clearer structure"}
        description={getSectionDescription("research", language)}
        tabs={SECTION_TABS.research.map((tab) => ({
          id: tab.id,
          label: tab.label[language],
          hint: tab.description?.[language],
        }))}
        activeTab={currentTab}
        onTabChange={(tab) => setActiveSection("research", tab)}
      >
        <AnalysisView />
      </SectionWorkspace>
    );
  }

  if (currentTab === "research-signal") {
    return (
      <SectionWorkspace
        eyebrow={language === "es" ? "Investigación" : "Research"}
        title={language === "es" ? "Explora ideas con una estructura más clara" : "Explore ideas with a clearer structure"}
        description={getSectionDescription("research", language)}
        tabs={SECTION_TABS.research.map((tab) => ({
          id: tab.id,
          label: tab.label[language],
          hint: tab.description?.[language],
        }))}
        activeTab={currentTab}
        onTabChange={(tab) => setActiveSection("research", tab)}
      >
        <PredictionView />
      </SectionWorkspace>
    );
  }

  return (
    <SectionWorkspace
      eyebrow={language === "es" ? "Investigación" : "Research"}
      title={language === "es" ? "Explora ideas con una estructura más clara" : "Explore ideas with a clearer structure"}
      description={getSectionDescription("research", language)}
      tabs={SECTION_TABS.research.map((tab) => ({
        id: tab.id,
        label: tab.label[language],
        hint: tab.description?.[language],
      }))}
      activeTab={currentTab}
      onTabChange={(tab) => setActiveSection("research", tab)}
      actions={
        <>
          <button
            onClick={() => loadRankings(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-oracle-accent/30 bg-oracle-accent/15 px-4 py-3 text-sm font-medium text-oracle-accent transition-colors hover:bg-oracle-accent/25"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            {language === "es" ? "Actualizar y guardar corte" : "Refresh + snapshot"}
          </button>
          <button
            onClick={async () => {
              await saveScreen({
                name: screenName,
                symbols: topSymbols,
                notes:
                  language === "es"
                    ? "Símbolos mejor puntuados en la vista actual."
                    : "Top ranked symbols from the current quant view.",
              });
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-oracle-border bg-oracle-bg/60 px-4 py-3 text-sm text-oracle-text transition-colors hover:bg-oracle-bg"
          >
            <BookmarkPlus className="h-4 w-4" />
            {language === "es" ? "Guardar pantalla" : "Save screen"}
          </button>
        </>
      }
      aside={
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={screenName}
            onChange={(event) => setScreenName(event.target.value)}
            className="w-full max-w-sm rounded-xl border border-oracle-border bg-oracle-bg/70 px-3 py-2 text-sm text-oracle-text placeholder:text-oracle-muted"
            placeholder={language === "es" ? "Nombre para guardar esta vista" : "Name for this saved screen"}
          />
          <div className="rounded-xl border border-oracle-border bg-oracle-bg/60 px-4 py-3 text-sm">
            <p className="text-oracle-muted">{language === "es" ? "Universo" : "Universe"}</p>
            <p className="mt-1 font-semibold text-oracle-text">{rankings?.universe.length ?? 0} {language === "es" ? "símbolos" : "symbols"}</p>
          </div>
          <div className="rounded-xl border border-oracle-border bg-oracle-bg/60 px-4 py-3 text-sm">
            <p className="text-oracle-muted">{language === "es" ? "Cortes guardados" : "Snapshots"}</p>
            <p className="mt-1 font-semibold text-oracle-text">{snapshots?.total ?? 0}</p>
          </div>
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1fr]">
        <section className="rounded-2xl border border-oracle-border bg-oracle-panel">
          <div className="border-b border-oracle-border px-4 py-3">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
              <Sigma className="h-3.5 w-3.5" />
              {language === "es" ? "Ideas priorizadas" : "Rankings"}
            </div>
            <p className="mt-1 text-sm text-oracle-muted">
              {language === "es"
                ? "Qué activos salen mejor parados cuando combinamos impulso reciente, revisiones, sentimiento y riesgo."
                : "Assets that stand out when combining momentum, revisions, sentiment and risk."}
            </p>
          </div>
          <div className="max-h-[72vh] overflow-y-auto p-3">
            <div className="space-y-3">
              {rankings?.rankings.map((entry) => (
                <button
                  key={entry.symbol}
                  onClick={() => setSelectedSymbol(entry.symbol)}
                  className={`w-full rounded-xl border p-4 text-left transition-colors ${
                    selectedSymbol === entry.symbol
                      ? "border-oracle-accent/50 bg-oracle-accent/10"
                      : "border-oracle-border bg-oracle-bg/40 hover:bg-oracle-bg"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <p className="text-lg font-semibold text-oracle-text">{entry.symbol}</p>
                    <span className="rounded-full border border-oracle-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-oracle-muted">
                      {getInboxKindLabel(entry.verdict, language)}
                    </span>
                    <span className="ml-auto text-sm font-mono text-oracle-accent">
                      {entry.composite_score.toFixed(1)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-oracle-muted">{entry.name}</p>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                    <div className="rounded-lg border border-oracle-border bg-oracle-panel/60 px-2 py-2">
                      <p className="text-oracle-muted">{language === "es" ? "Impulso reciente" : "Momentum"}</p>
                      <p className={`mt-1 font-mono ${factorColor(entry.factors.momentum)}`}>{entry.factors.momentum.toFixed(0)}</p>
                    </div>
                    <div className="rounded-lg border border-oracle-border bg-oracle-panel/60 px-2 py-2">
                      <p className="text-oracle-muted">{language === "es" ? "Sentimiento" : "Sentiment"}</p>
                      <p className={`mt-1 font-mono ${factorColor(entry.factors.sentiment)}`}>{entry.factors.sentiment.toFixed(0)}</p>
                    </div>
                    <div className="rounded-lg border border-oracle-border bg-oracle-panel/60 px-2 py-2">
                      <p className="text-oracle-muted">{language === "es" ? "Riesgo" : "Risk"}</p>
                      <p className={`mt-1 font-mono ${factorColor(entry.factors.risk)}`}>{entry.factors.risk.toFixed(0)}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
            {loading && !rankings ? <p className="text-sm text-oracle-muted">{language === "es" ? "Cargando ideas..." : "Loading rankings..."}</p> : null}
            {error ? <p className="text-sm text-oracle-red">{error}</p> : null}
          </div>
        </section>

        <section className="space-y-4">
          <div className="rounded-2xl border border-oracle-border bg-oracle-panel">
            <div className="border-b border-oracle-border px-4 py-3">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
                <BarChart3 className="h-3.5 w-3.5" />
                {language === "es" ? "Qué explica esta idea" : "Factor detail"}
              </div>
              <p className="mt-1 text-sm text-oracle-muted">{selectedSymbol || (language === "es" ? "Selecciona un símbolo" : "Select a symbol")}</p>
            </div>
            {factors ? (
              <div className="space-y-4 p-5">
                <div className="flex flex-wrap items-start gap-3">
                  <div>
                    <h3 className="text-xl font-semibold text-oracle-text">{factors.symbol}</h3>
                    <p className="mt-1 text-sm text-oracle-muted">
                      {language === "es"
                        ? `Lectura ${factors.verdict} · régimen ${factors.regime} · fiabilidad ${getConfidenceBand(factors.confidence, language).toLowerCase()} ${(factors.confidence * 100).toFixed(0)}%`
                        : `Verdict ${factors.verdict} · regime ${factors.regime} · confidence ${(factors.confidence * 100).toFixed(0)}%`}
                    </p>
                  </div>
                  <div className="ml-auto rounded-2xl border border-oracle-border bg-oracle-bg/60 px-4 py-3">
                    <p className="text-[11px] uppercase tracking-wide text-oracle-muted">{language === "es" ? "Puntuación global" : "Composite"}</p>
                    <p className="mt-1 text-2xl font-semibold text-oracle-accent">
                      {factors.composite_score.toFixed(1)}
                    </p>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {Object.entries(factors.factors).map(([name, value]) => (
                    <div key={name} className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                      <p className="text-[11px] uppercase tracking-wide text-oracle-muted">{name}</p>
                      <p className={`mt-2 text-lg font-semibold ${factorColor(value)}`}>{value.toFixed(1)}</p>
                    </div>
                  ))}
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                    <p className="text-[11px] uppercase tracking-wide text-oracle-muted">{language === "es" ? "Métricas de riesgo" : "Risk metrics"}</p>
                    <div className="mt-3 space-y-2 text-sm text-oracle-text">
                      {Object.entries(factors.risk_metrics).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between">
                          <span className="text-oracle-muted">{key}</span>
                          <span className="font-mono">{typeof value === "number" ? value.toFixed(3) : String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                    <p className="text-[11px] uppercase tracking-wide text-oracle-muted">{language === "es" ? "Patrones visibles" : "Candlestick patterns"}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {factors.candlestick_patterns.length > 0 ? factors.candlestick_patterns.map((pattern) => (
                        <span key={pattern} className="rounded-full border border-oracle-border px-2 py-1 text-xs text-oracle-text">
                          {pattern}
                        </span>
                      )) : <span className="text-sm text-oracle-muted">{language === "es" ? "No hay patrones dominantes" : "No dominant patterns"}</span>}
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => {
                    setGlobalSymbol(factors.symbol);
                    openAssetDetail(factors.symbol);
                  }}
                  className="rounded-lg border border-oracle-accent/30 bg-oracle-accent/15 px-3 py-2 text-sm text-oracle-accent transition-colors hover:bg-oracle-accent/20"
                >
                  {language === "es" ? "Abrir detalle del activo" : "Open asset detail"}
                </button>
              </div>
            ) : (
              <div className="p-6 text-sm text-oracle-muted">{language === "es" ? "Selecciona una idea para entender qué la apoya o la frena." : "Select an idea to understand what supports it or weakens it."}</div>
            )}
          </div>

          <div className="rounded-2xl border border-oracle-border bg-oracle-panel">
            <div className="border-b border-oracle-border px-4 py-3">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
                <Database className="h-3.5 w-3.5" />
                Cortes guardados
              </div>
              <p className="mt-1 text-sm text-oracle-muted">{language === "es" ? "Validación ligera para ver si una señal tuvo sentido después." : "Light validation to see whether a signal worked afterwards."}</p>
            </div>
            <div className="space-y-3 p-4">
              {(snapshots?.snapshots ?? []).slice(0, 4).map((snapshot) => (
                <div key={snapshot.id} className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-oracle-text">{snapshot.name}</p>
                      <p className="text-xs text-oracle-muted">
                        {snapshot.universe.length} símbolos · {new Date(snapshot.captured_at).toLocaleString()}
                      </p>
                    </div>
                    <span className="text-xs font-mono text-oracle-muted">
                      {snapshot.rankings.length} {language === "es" ? "puestos" : "ranks"}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {snapshot.validation.map((item) => (
                      <span key={`${snapshot.id}-${item.horizon}`} className="rounded-full border border-oracle-border px-2 py-1 text-xs text-oracle-text">
                        {item.horizon.toUpperCase()} · media {(item.average_return * 100).toFixed(1)}%
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {(snapshots?.snapshots ?? []).length === 0 ? (
                <p className="text-sm text-oracle-muted">{language === "es" ? "Aún no hay cortes guardados." : "No snapshots saved yet."}</p>
              ) : null}
            </div>
          </div>
        </section>
      </div>
    </SectionWorkspace>
  );
}
