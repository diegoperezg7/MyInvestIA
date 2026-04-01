"use client";

import { CalendarDays, Globe2, Newspaper, Radar, ScanLine } from "lucide-react";

import BreakingNewsFeed from "@/components/dashboard/BreakingNewsFeed";
import MarketOverviewCard from "@/components/dashboard/MarketOverviewCard";
import SectionWorkspace from "@/components/layout/SectionWorkspace";
import CommoditiesView from "@/components/views/CommoditiesView";
import EconomicCalendarView from "@/components/views/EconomicCalendarView";
import HeatmapView from "@/components/views/HeatmapView";
import MacroView from "@/components/views/MacroView";
import MoversView from "@/components/views/MoversView";
import VolatilityView from "@/components/views/VolatilityView";
import { SECTION_TABS, getSectionDescription } from "@/lib/shell";
import useLanguageStore from "@/stores/useLanguageStore";
import { useView } from "@/contexts/ViewContext";
import type { SectionTabId } from "@/types";

function marketsTabLabel(tab: SectionTabId, language: "es" | "en") {
  const tabCopy = SECTION_TABS.markets.find((item) => item.id === tab);
  return tabCopy?.label[language] ?? tab;
}

export default function MarketsView() {
  const { activeTab, setActiveSection } = useView();
  const language = useLanguageStore((state) => state.language);
  const currentTab = activeTab.startsWith("markets-")
    ? activeTab
    : "markets-today";

  return (
    <SectionWorkspace
      eyebrow={language === "es" ? "Mercados" : "Markets"}
      title={language === "es" ? "Contexto antes de abrir una posición" : "Context before opening a position"}
      description={getSectionDescription("markets", language)}
      tabs={SECTION_TABS.markets.map((tab) => ({
        id: tab.id,
        label: marketsTabLabel(tab.id, language),
        hint: tab.description?.[language],
      }))}
      activeTab={currentTab}
      onTabChange={(tab) => setActiveSection("markets", tab)}
      aside={
        <div className="grid gap-3 lg:grid-cols-4">
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <Radar className="h-4 w-4 text-oracle-accent" />
              {language === "es" ? "Pulso del día" : "Daily pulse"}
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Una lectura rápida de cómo viene el día."
                : "A quick read of how the day is shaping up."}
            </p>
          </div>
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <Globe2 className="h-4 w-4 text-oracle-accent" />
              Macro
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Indicadores y eventos que pueden mover todo el mercado."
                : "Indicators and events that can move the whole market."}
            </p>
          </div>
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <CalendarDays className="h-4 w-4 text-oracle-accent" />
              {language === "es" ? "Calendario" : "Calendar"}
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Lo próximo que puede cambiar el tono del mercado."
                : "What can change market tone next."}
            </p>
          </div>
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <Newspaper className="h-4 w-4 text-oracle-accent" />
              {language === "es" ? "Señales visibles" : "Visible signals"}
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Noticias, movers y volatilidad para no ir a ciegas."
                : "News, movers and volatility so you are not flying blind."}
            </p>
          </div>
        </div>
      }
    >
      {currentTab === "markets-today" ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.85fr_1.15fr]">
          <div className="space-y-4">
            <MarketOverviewCard />
            <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-4">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
                <ScanLine className="h-3.5 w-3.5" />
                {language === "es" ? "Movimientos destacados" : "Key moves"}
              </div>
              <p className="mt-1 text-sm text-oracle-muted">
                {language === "es"
                  ? "Quién se mueve más hoy y por qué merece atención."
                  : "Who is moving the most today and why it matters."}
              </p>
              <div className="mt-4">
                <MoversView />
              </div>
            </div>
          </div>
          <BreakingNewsFeed defaultCollapsed={false} />
        </div>
      ) : null}

      {currentTab === "markets-macro" ? <MacroView /> : null}
      {currentTab === "markets-calendar" ? <EconomicCalendarView /> : null}

      {currentTab === "markets-moves" ? (
        <div className="space-y-4">
          <MoversView />
          <VolatilityView />
        </div>
      ) : null}

      {currentTab === "markets-maps" ? (
        <div className="space-y-4">
          <HeatmapView />
          <CommoditiesView />
        </div>
      ) : null}
    </SectionWorkspace>
  );
}
