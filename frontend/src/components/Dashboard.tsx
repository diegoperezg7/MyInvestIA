"use client";

import { useView } from "@/contexts/ViewContext";
import useLanguageStore from "@/stores/useLanguageStore";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import MobileTopBar from "@/components/layout/MobileTopBar";
import KeyboardShortcuts from "@/components/layout/KeyboardShortcuts";
import CommandBar from "@/components/layout/CommandBar";
import MobileBottomNav from "@/components/layout/MobileBottomNav";

import OverviewView from "@/components/views/OverviewView";
import TerminalView from "@/components/views/TerminalView";
import InboxView from "@/components/views/InboxView";
import SettingsView from "@/components/views/SettingsView";
import PortfolioView from "@/components/views/PortfolioView";
import ResearchView from "@/components/views/ResearchView";
import MarketsView from "@/components/views/MarketsView";
import AssistantView from "@/components/views/AssistantView";

const SECTION_MAP: Record<string, React.ComponentType> = {
  home: OverviewView,
  priorities: InboxView,
  portfolio: PortfolioView,
  research: ResearchView,
  markets: MarketsView,
  assistant: AssistantView,
  settings: SettingsView,
};

export default function Dashboard() {
  const { activeSection, focusView, sidebarCollapsed } = useView();
  const t = useLanguageStore((s) => s.t);
  const ActiveComponent = SECTION_MAP[activeSection] || OverviewView;
  const isAssetDetail = focusView === "asset-detail";

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <KeyboardShortcuts />
      <CommandBar />
      <MobileBottomNav />

      <div
        className={`flex flex-col flex-1 min-h-screen transition-all duration-300 ${
          sidebarCollapsed ? "lg:ml-16" : "lg:ml-64"
        }`}
      >
        <TopBar />
        <MobileTopBar />

        <main className="flex-1 p-3 pb-24 sm:p-4 sm:pb-24 lg:p-6 lg:pb-6">
          <div key={isAssetDetail ? "terminal" : activeSection} className="view-transition">
            {isAssetDetail ? <TerminalView /> : <ActiveComponent />}
          </div>
        </main>

        <footer className="pt-4 pb-6 text-center text-oracle-muted text-xs">
          <p>{t("footer.disclaimer")}</p>
        </footer>
      </div>
    </div>
  );
}
