"use client";

import {
  LayoutDashboard,
  BarChart3,
  ScanSearch,
  TrendingUp,
  Activity,
  Gem,
  PlayCircle,
  Bell,
  MessageSquare,
  Globe,
  Lightbulb,
  Crosshair,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useView, type View } from "@/contexts/ViewContext";
import useLanguageStore from "@/stores/useLanguageStore";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  key: View;
  labelKey: string;
  icon: LucideIcon;
  shortcut: string;
}

interface NavGroup {
  titleKey: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    titleKey: "group.core",
    items: [
      { key: "overview", labelKey: "nav.overview", icon: LayoutDashboard, shortcut: "1" },
      { key: "analysis", labelKey: "nav.analysis", icon: BarChart3, shortcut: "2" },
      { key: "screener", labelKey: "nav.screener", icon: ScanSearch, shortcut: "3" },
    ],
  },
  {
    titleKey: "group.markets",
    items: [
      { key: "movers", labelKey: "nav.movers", icon: TrendingUp, shortcut: "4" },
      { key: "volatility", labelKey: "nav.volatility", icon: Activity, shortcut: "5" },
      { key: "commodities", labelKey: "nav.commodities", icon: Gem, shortcut: "6" },
    ],
  },
  {
    titleKey: "group.intelligence",
    items: [
      { key: "prediction", labelKey: "nav.prediction", icon: Crosshair, shortcut: "7" },
      { key: "recommendations", labelKey: "nav.recommendations", icon: Lightbulb, shortcut: "8" },
      { key: "chat", labelKey: "nav.chat", icon: MessageSquare, shortcut: "9" },
      { key: "macro", labelKey: "nav.macro", icon: Globe, shortcut: "" },
    ],
  },
  {
    titleKey: "group.tools",
    items: [
      { key: "paper-trade", labelKey: "nav.paper_trade", icon: PlayCircle, shortcut: "" },
      { key: "alerts", labelKey: "nav.alerts", icon: Bell, shortcut: "0" },
    ],
  },
];

export default function Sidebar() {
  const {
    activeView,
    setActiveView,
    sidebarCollapsed,
    setSidebarCollapsed,
    sidebarMobileOpen,
    setSidebarMobileOpen,
  } = useView();
  const { t } = useLanguageStore();

  const handleNav = (view: View) => {
    setActiveView(view);
    setSidebarMobileOpen(false);
  };

  const sidebarContent = (
    <div className="flex flex-col h-full oracle-sidebar">
      {/* Branding + collapse toggle */}
      <div className="flex items-center justify-between h-14 px-4 border-b border-oracle-border shrink-0">
        {sidebarCollapsed ? (
          <span className="font-bold text-base tracking-wider">
            <span className="text-oracle-text">M</span>
            <span style={{ color: "var(--oracle-primary)" }}>I</span>
          </span>
        ) : (
          <span className="font-bold text-base tracking-wider">
            <span className="text-oracle-text">MyInvest</span>
            <span style={{ color: "var(--oracle-primary)" }}>IA</span>
          </span>
        )}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="p-1 text-oracle-muted hover:text-oracle-text rounded-md hover:bg-oracle-panel-hover transition-colors"
        >
          {sidebarCollapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        {NAV_GROUPS.map((group) => (
          <div key={group.titleKey} className="mb-6">
            {!sidebarCollapsed && (
              <p className="text-oracle-muted text-[10px] font-semibold uppercase tracking-widest px-3 mb-2">
                {t(group.titleKey)}
              </p>
            )}
            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive = activeView === item.key;
                const Icon = item.icon;
                return (
                  <button
                    key={item.key}
                    onClick={() => handleNav(item.key)}
                    title={sidebarCollapsed ? t(item.labelKey) : undefined}
                    className={`w-full flex items-center gap-3 rounded-md text-sm transition-colors duration-150 ${
                      sidebarCollapsed ? "justify-center px-2 py-3" : "px-3 py-2.5"
                    } ${
                      isActive
                        ? "oracle-nav-active text-oracle-accent"
                        : "text-oracle-muted hover:text-oracle-text hover:bg-oracle-panel-hover"
                    }`}
                  >
                    <Icon size={18} className="shrink-0" />
                    {!sidebarCollapsed && (
                      <span className="flex-1 text-left">{t(item.labelKey)}</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={`hidden lg:flex flex-col fixed left-0 top-0 h-screen border-r border-oracle-border z-40 transition-all duration-300 ${
          sidebarCollapsed ? "w-16" : "w-56"
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile overlay */}
      {sidebarMobileOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-40 lg:hidden"
            onClick={() => setSidebarMobileOpen(false)}
          />
          <aside className="fixed left-0 top-0 h-screen w-56 border-r border-oracle-border z-50 lg:hidden">
            {sidebarContent}
          </aside>
        </>
      )}
    </>
  );
}
