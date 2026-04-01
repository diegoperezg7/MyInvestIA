"use client";

import { BookOpenText, BriefcaseBusiness, ListChecks } from "lucide-react";

import AlertsView from "@/components/views/AlertsView";
import BreakingNewsFeed from "@/components/dashboard/BreakingNewsFeed";
import PortfolioSummary from "@/components/dashboard/PortfolioSummary";
import QuoteLookup from "@/components/dashboard/QuoteLookup";
import WatchlistCard from "@/components/dashboard/WatchlistCard";
import SectionWorkspace from "@/components/layout/SectionWorkspace";
import ThesesView from "@/components/views/ThesesView";
import { SECTION_TABS, getSectionDescription } from "@/lib/shell";
import useLanguageStore from "@/stores/useLanguageStore";
import { useView } from "@/contexts/ViewContext";
import type { SectionTabId } from "@/types";

function portfolioTabLabel(tab: SectionTabId, language: "es" | "en") {
  const tabCopy = SECTION_TABS.portfolio.find((item) => item.id === tab);
  return tabCopy?.label[language] ?? tab;
}

export default function PortfolioView() {
  const { activeTab, setActiveSection } = useView();
  const language = useLanguageStore((state) => state.language);
  const currentTab = activeTab.startsWith("portfolio-")
    ? activeTab
    : "portfolio-overview";

  return (
    <SectionWorkspace
      eyebrow={language === "es" ? "Cartera" : "Portfolio"}
      title={language === "es" ? "Todo lo que afecta a tus activos" : "Everything affecting your assets"}
      description={getSectionDescription("portfolio", language)}
      tabs={SECTION_TABS.portfolio.map((tab) => ({
        id: tab.id,
        label: portfolioTabLabel(tab.id, language),
        hint: tab.description?.[language],
      }))}
      activeTab={currentTab}
      onTabChange={(tab) => setActiveSection("portfolio", tab)}
      aside={
        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <BriefcaseBusiness className="h-4 w-4 text-oracle-accent" />
              {language === "es" ? "Posiciones y riesgo" : "Positions & risk"}
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Aquí ves cuánto tienes, cuánto arriesgas y dónde estás más expuesto."
                : "See what you hold, what you risk and where you are most exposed."}
            </p>
          </div>
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <ListChecks className="h-4 w-4 text-oracle-accent" />
              Watchlists
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Mantén cerca lo que todavía no tienes en cartera, pero vigilarías."
                : "Keep close what is not in the portfolio yet but worth watching."}
            </p>
          </div>
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <BookOpenText className="h-4 w-4 text-oracle-accent" />
              {language === "es" ? "Tesis y alertas" : "Theses & alerts"}
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Tus ideas, revisiones y avisos deben vivir junto a la cartera, no aparte."
                : "Ideas, reviews and alerts should live next to the portfolio, not apart."}
            </p>
          </div>
        </div>
      }
    >
      {currentTab === "portfolio-overview" ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-4">
            <PortfolioSummary />
          </div>
          <div className="space-y-4">
            <QuoteLookup />
            <BreakingNewsFeed defaultCollapsed={false} />
          </div>
        </div>
      ) : null}

      {currentTab === "portfolio-watchlists" ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <WatchlistCard defaultCollapsed={false} />
          <BreakingNewsFeed defaultCollapsed={false} />
        </div>
      ) : null}

      {currentTab === "portfolio-theses" ? <ThesesView embedded /> : null}
      {currentTab === "portfolio-alerts" ? <AlertsView /> : null}
    </SectionWorkspace>
  );
}
