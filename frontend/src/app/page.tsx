"use client";

import { useView } from "@/contexts/ViewContext";
import useLanguageStore from "@/stores/useLanguageStore";
import Sidebar from "@/components/layout/Sidebar";
import MobileTopBar from "@/components/layout/MobileTopBar";
import HeroMetrics from "@/components/layout/HeroMetrics";
import KeyboardShortcuts from "@/components/layout/KeyboardShortcuts";
import CommandBar from "@/components/layout/CommandBar";

import OverviewView from "@/components/views/OverviewView";
import AnalysisView from "@/components/views/AnalysisView";
import ScreenerView from "@/components/views/ScreenerView";
import MoversView from "@/components/views/MoversView";
import VolatilityView from "@/components/views/VolatilityView";
import PaperTradingView from "@/components/views/PaperTradingView";
import AlertsView from "@/components/views/AlertsView";
import ChatView from "@/components/views/ChatView";
import MacroView from "@/components/views/MacroView";
import CommoditiesView from "@/components/views/CommoditiesView";
import RecommendationsView from "@/components/views/RecommendationsView";
import PredictionView from "@/components/views/PredictionView";

const VIEW_MAP: Record<string, React.ComponentType> = {
  overview: OverviewView,
  analysis: AnalysisView,
  screener: ScreenerView,
  movers: MoversView,
  volatility: VolatilityView,
  commodities: CommoditiesView,
  "paper-trade": PaperTradingView,
  alerts: AlertsView,
  chat: ChatView,
  macro: MacroView,
  recommendations: RecommendationsView,
  prediction: PredictionView,
};

export default function Home() {
  const { activeView, sidebarCollapsed } = useView();
  const t = useLanguageStore((s) => s.t);
  const ActiveComponent = VIEW_MAP[activeView] || OverviewView;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <KeyboardShortcuts />
      <CommandBar />

      <div
        className={`flex flex-col flex-1 min-h-screen transition-all duration-300 ${
          sidebarCollapsed ? "lg:ml-16" : "lg:ml-56"
        }`}
      >
        <MobileTopBar />

        <main className="flex-1 p-6">
          <HeroMetrics />
          <div key={activeView} className="view-transition">
            <ActiveComponent />
          </div>
        </main>

        <footer className="pt-4 pb-6 text-center text-oracle-muted text-xs">
          <p>{t("footer.disclaimer")}</p>
        </footer>
      </div>
    </div>
  );
}
