"use client";

import {
  BriefcaseBusiness,
  ChevronsLeft,
  ChevronsRight,
  Compass,
  Home,
  Inbox,
  MessageSquareText,
  Search,
  Settings,
  TrendingUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { useView } from "@/contexts/ViewContext";
import { getSectionDescription, getSectionLabel, type LocalizedCopy } from "@/lib/shell";
import type { SectionId } from "@/types";
import useLanguageStore from "@/stores/useLanguageStore";

interface NavItem {
  id: SectionId;
  icon: LucideIcon;
  eyebrow?: LocalizedCopy;
}

const PRIMARY_ITEMS: NavItem[] = [
  { id: "home", icon: Home },
  { id: "priorities", icon: Inbox },
  { id: "portfolio", icon: BriefcaseBusiness },
];

const SECONDARY_ITEMS: NavItem[] = [
  { id: "research", icon: Search },
  { id: "markets", icon: TrendingUp },
  { id: "assistant", icon: MessageSquareText },
];

function NavButton({
  active,
  collapsed,
  label,
  description,
  icon: Icon,
  onClick,
}: {
  active: boolean;
  collapsed: boolean;
  label: string;
  description: string;
  icon: LucideIcon;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? label : undefined}
      className={`w-full rounded-xl text-left transition-colors ${
        active
          ? "oracle-nav-active text-oracle-accent"
          : "text-oracle-muted hover:bg-oracle-panel-hover hover:text-oracle-text"
      } ${collapsed ? "flex justify-center px-2 py-3" : "flex items-start gap-3 px-3 py-3"}`}
    >
      <Icon className="mt-0.5 h-4.5 w-4.5 shrink-0" />
      {!collapsed ? (
        <span className="min-w-0">
          <span className="block text-sm font-medium">{label}</span>
          <span className="mt-1 block text-xs leading-5 text-oracle-muted">
            {description}
          </span>
        </span>
      ) : null}
    </button>
  );
}

function NavGroup({
  collapsed,
  items,
  language,
  onSelect,
  title,
  activeSection,
  focusView,
}: {
  collapsed: boolean;
  items: NavItem[];
  language: "es" | "en";
  onSelect: (section: SectionId) => void;
  title: string;
  activeSection: SectionId;
  focusView: "asset-detail" | null;
}) {
  return (
    <div className="mb-6">
      {!collapsed ? (
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
          {title}
        </p>
      ) : null}
      <div className="space-y-1">
        {items.map((item) => (
          <NavButton
            key={item.id}
            active={focusView === null && activeSection === item.id}
            collapsed={collapsed}
            label={getSectionLabel(item.id, language)}
            description={getSectionDescription(item.id, language)}
            icon={item.icon}
            onClick={() => onSelect(item.id)}
          />
        ))}
      </div>
    </div>
  );
}

export default function Sidebar() {
  const {
    activeSection,
    focusView,
    openAssetDetail,
    sidebarCollapsed,
    setActiveSection,
    setSidebarCollapsed,
    sidebarMobileOpen,
    setSidebarMobileOpen,
    selectedSymbol,
    setActiveView,
  } = useView();
  const language = useLanguageStore((state) => state.language);

  const sidebarContent = (
    <div className="oracle-sidebar flex h-full flex-col">
      <div className="flex h-14 items-center justify-between border-b border-oracle-border px-4 shrink-0">
        {sidebarCollapsed ? (
          <span className="text-base font-bold tracking-wider">
            <span className="text-oracle-text">M</span>
            <span style={{ color: "var(--oracle-primary)" }}>I</span>
          </span>
        ) : (
          <div>
            <span className="text-base font-bold tracking-wider">
              <span className="text-oracle-text">MyInvest</span>
              <span style={{ color: "var(--oracle-primary)" }}>IA</span>
            </span>
            <p className="mt-0.5 text-[11px] text-oracle-muted">
              {language === "es"
                ? "Menos pantallas, más claridad"
                : "Less clutter, more clarity"}
            </p>
          </div>
        )}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="rounded-md p-1 text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
          aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-4">
        <NavGroup
          collapsed={sidebarCollapsed}
          items={PRIMARY_ITEMS}
          language={language}
          onSelect={(section) => {
            setActiveSection(section);
            setSidebarMobileOpen(false);
          }}
          title={language === "es" ? "Principal" : "Core"}
          activeSection={activeSection}
          focusView={focusView}
        />
        <NavGroup
          collapsed={sidebarCollapsed}
          items={SECONDARY_ITEMS}
          language={language}
          onSelect={(section) => {
            setActiveSection(section);
            setSidebarMobileOpen(false);
          }}
          title={language === "es" ? "Explorar" : "Explore"}
          activeSection={activeSection}
          focusView={focusView}
        />

        <div className="mb-6">
          {!sidebarCollapsed ? (
            <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
              {language === "es" ? "Accesos" : "Shortcuts"}
            </p>
          ) : null}
          <div className="space-y-1">
            <button
              onClick={() => {
                if (selectedSymbol) {
                  openAssetDetail(selectedSymbol);
                } else {
                  openAssetDetail();
                }
                setSidebarMobileOpen(false);
              }}
              title={
                sidebarCollapsed
                  ? language === "es"
                    ? "Detalle del activo"
                    : "Asset detail"
                  : undefined
              }
              className={`w-full rounded-xl transition-colors ${
                focusView === "asset-detail"
                  ? "oracle-nav-active text-oracle-accent"
                  : "text-oracle-muted hover:bg-oracle-panel-hover hover:text-oracle-text"
              } ${sidebarCollapsed ? "flex justify-center px-2 py-3" : "flex items-start gap-3 px-3 py-3 text-left"}`}
            >
              <Compass className="mt-0.5 h-4.5 w-4.5 shrink-0" />
              {!sidebarCollapsed ? (
                <span className="min-w-0">
                  <span className="block text-sm font-medium">
                    {language === "es" ? "Detalle del activo" : "Asset detail"}
                  </span>
                  <span className="mt-1 block text-xs leading-5 text-oracle-muted">
                    {selectedSymbol
                      ? `${language === "es" ? "Abre el contexto completo de" : "Open the full context for"} ${selectedSymbol}`
                      : language === "es"
                        ? "Profundiza en un símbolo desde cualquier sección"
                        : "Dive into any symbol from any section"}
                  </span>
                </span>
              ) : null}
            </button>
          </div>
        </div>
      </nav>

      <div className="mt-auto border-t border-oracle-border px-2 pb-4 pt-4">
        <div className="space-y-1">
          <NavButton
            active={focusView === null && activeSection === "settings"}
            collapsed={sidebarCollapsed}
            label={getSectionLabel("settings", language)}
            description={getSectionDescription("settings", language)}
            icon={Settings}
            onClick={() => {
              setActiveView("settings");
              setSidebarMobileOpen(false);
            }}
          />
          <a
            href={process.env.NEXT_PUBLIC_PORTAL_URL || "/"}
            className={`w-full rounded-xl text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text ${
              sidebarCollapsed ? "flex justify-center px-2 py-3" : "flex items-start gap-3 px-3 py-3 text-left"
            }`}
          >
            <Home className="mt-0.5 h-4.5 w-4.5 shrink-0" />
            {!sidebarCollapsed ? (
              <span className="min-w-0">
                <span className="block text-sm font-medium">
                  {language === "es" ? "Portal" : "Portal"}
                </span>
                <span className="mt-1 block text-xs leading-5 text-oracle-muted">
                  {language === "es"
                    ? "Volver al portal principal"
                    : "Return to the main portal"}
                </span>
              </span>
            ) : null}
          </a>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <aside
        className={`fixed left-0 top-0 z-40 hidden h-screen flex-col border-r border-oracle-border transition-all duration-300 lg:flex ${
          sidebarCollapsed ? "w-16" : "w-64"
        }`}
      >
        {sidebarContent}
      </aside>

      {sidebarMobileOpen ? (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 lg:hidden"
            onClick={() => setSidebarMobileOpen(false)}
            onKeyDown={(event) => {
              if (event.key === "Escape" || event.key === "Enter" || event.key === " ") {
                setSidebarMobileOpen(false);
              }
            }}
            role="button"
            tabIndex={0}
          />
          <aside className="fixed left-0 top-0 z-50 h-screen w-72 border-r border-oracle-border lg:hidden">
            {sidebarContent}
          </aside>
        </>
      ) : null}
    </>
  );
}
